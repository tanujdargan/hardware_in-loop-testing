import json
import time
from .serial_utils import SerialConnection # Assuming SerialConnection is defined

def emulate_from_file(input_json_path: str, serial_conn: SerialConnection):
    """
    Parses the input JSON file and executes the emulation sequence.
    Args:
        input_json_path (str): Path to the JSON file defining input emulation.
        serial_conn (SerialConnection): An active serial connection object.
    Returns:
        dict: The parsed input JSON data (or None if error).
    """
    try:
        with open(input_json_path, 'r') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input JSON file not found at '{input_json_path}'")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Could not decode Input JSON file '{input_json_path}': {e}")
        return None

    test_name = input_data.get("test_name", "Unnamed Test")
    emulation_sequence = input_data.get("emulation_sequence", [])

    print(f"\nStarting Input Emulation for: {test_name}")
    if not emulation_sequence:
        print("Warning: No emulation sequence found in input JSON.")
        return input_data # Return data even if sequence is empty

    for action in emulation_sequence:
        action_id = action.get("action_id", "N/A")
        action_type = action.get("type")
        description = action.get("description", "")
        
        print(f"  Executing Action ID: {action_id} | Type: {action_type} | Desc: {description}")

        if action_type == "send_serial_line":
            payload = action.get("payload")
            if payload is None:
                print(f"    Error: 'payload' missing for send_serial_line action '{action_id}'. Skipping.")
                continue
            if not serial_conn.send_line(str(payload)):
                print(f"    Failed to send serial line for action '{action_id}'. Halting emulation.")
                return input_data # Return data, but indicate failure upstream
            print(f"    Sent line: '{payload}'")

        elif action_type == "send_serial_bytes":
            payload_hex = action.get("payload_hex")
            if payload_hex is None:
                print(f"    Error: 'payload_hex' missing for send_serial_bytes action '{action_id}'. Skipping.")
                continue
            try:
                byte_data = bytes.fromhex(payload_hex)
                if not serial_conn.send_bytes(byte_data):
                    print(f"    Failed to send serial bytes for action '{action_id}'. Halting emulation.")
                    return input_data
                print(f"    Sent bytes: {payload_hex}")
            except ValueError:
                print(f"    Error: Invalid hex string '{payload_hex}' for action '{action_id}'. Skipping.")
                continue
        
        elif action_type == "delay_ms":
            duration = action.get("duration")
            if duration is None:
                print(f"    Error: 'duration' missing for delay_ms action '{action_id}'. Skipping.")
                continue
            try:
                delay_seconds = int(duration) / 1000.0
                if delay_seconds < 0:
                    print("    Warning: Negative delay duration. Skipping delay.")
                else:
                    print(f"    Delaying for {duration} ms...")
                    time.sleep(delay_seconds)
            except ValueError:
                 print(f"    Error: Invalid duration '{duration}' for action '{action_id}'. Skipping.")
                 continue
        else:
            print(f"    Warning: Unknown action type '{action_type}' for action_id '{action_id}'. Skipping.")
        
        time.sleep(0.05) # Small breather between actions

    print("Input Emulation Finished.")
    return input_data # Return the parsed data for potential use in output checking fallback 