import json
import time
from .gpio_controller import GPIOController, GPIOControllerError

def emulate_hw_pins_from_file(input_json_path: str, gpio_ctrl: GPIOController):
    """
    Parses input JSON and executes hardware pin emulation sequences.
    Returns the parsed input_data on success or for continuing partially, None on critical parse error.
    """
    try:
        with open(input_json_path, 'r') as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"PinEmulator Error: Hardware Input Actions JSON file not found at '{input_json_path}'")
        return None
    except json.JSONDecodeError as e:
        print(f"PinEmulator Error: Could not decode Input JSON file '{input_json_path}': {e}")
        return None

    test_name = input_data.get("test_name", "Unnamed Hardware Test")
    # GPIO mode setup is handled by GPIOController's initialization
    
    emulation_sequence = input_data.get("emulation_sequence", [])
    print(f"\nStarting Hardware Pin Emulation for: {test_name}")

    if not emulation_sequence:
        print("PinEmulator Warning: No emulation sequence found in input JSON.")
        return input_data # Return data, sequence was empty

    sequence_successful = True
    for action_index, action in enumerate(emulation_sequence):
        action_id = action.get("action_id", f"action_{action_index}")
        action_type = action.get("type")
        description = action.get("description", "")
        pin = action.get("pin")

        print(f"  Executing Action ID: {action_id} | Type: {action_type} | Pin: {pin or 'N/A'} | Desc: {description}")

        try:
            if action_type == "set_gpio_direction":
                if pin is None or "direction" not in action:
                    print(f"    Error in '{action_id}': 'pin' and 'direction' required. Skipping.")
                    sequence_successful = False; continue
                gpio_ctrl.setup_pin_direction(pin, action["direction"],
                                              action.get("initial_state"),
                                              action.get("pull_up_down"))
            elif action_type == "set_gpio_output":
                if pin is None or "value" not in action:
                    print(f"    Error in '{action_id}': 'pin' and 'value' required. Skipping.")
                    sequence_successful = False; continue
                gpio_ctrl.set_pin_output(pin, action["value"])
            elif action_type == "read_gpio_input": # Primarily for RPi to log, not for STM32 test validation
                if pin is None:
                    print(f"    Error in '{action_id}': 'pin' required. Skipping.")
                    sequence_successful = False; continue
                state = gpio_ctrl.read_pin_input(pin)
                # This read value is not directly used to validate STM32 output here.
                # STM32 would react to RPi's output pins, then send its own state via serial.
                print(f"    RPi read GPIO Pin {pin} state: {state}")
            elif action_type == "pulse_gpio_output":
                if pin is None or "duration_ms" not in action:
                    print(f"    Error in '{action_id}': 'pin' and 'duration_ms' required. Skipping.")
                    sequence_successful = False; continue
                gpio_ctrl.pulse_pin_output(pin, action["duration_ms"],
                                           action.get("pulse_state", "high"),
                                           action.get("initial_state"))
            elif action_type == "delay_ms":
                duration = action.get("duration")
                if duration is None:
                    print(f"    Error in '{action_id}': 'duration' missing. Skipping.")
                    sequence_successful = False; continue
                if not isinstance(duration, (int, float)) or duration < 0:
                    print(f"    Error in '{action_id}': 'duration' must be a non-negative number. Got {duration}. Skipping.")
                    sequence_successful = False; continue
                print(f"    Delaying for {duration} ms...")
                time.sleep(float(duration) / 1000.0)
            # ... (SPI/I2C conceptual placeholders) ...
            else:
                print(f"    Warning in '{action_id}': Unknown action type '{action_type}'. Skipping.")
                sequence_successful = False # Consider unknown action a partial failure
        
        except GPIOControllerError as e:
            print(f"    GPIO Control ERROR during action '{action_id}': {e}")
            sequence_successful = False
            # Decide if to break or continue: for now, continue to attempt other actions.
            # If a critical setup fails, subsequent actions might also fail or behave unexpectedly.
        except Exception as e:
            print(f"    Unexpected ERROR during action '{action_id}': {e}")
            sequence_successful = False
            
        time.sleep(0.01) # Small fixed breather after each action

    if not sequence_successful:
        print("Hardware Pin Emulation Finished with one or more errors/skipped actions.")
    else:
        print("Hardware Pin Emulation Finished successfully.")
    return input_data # Return original data; success status is internal or handled by main runner 