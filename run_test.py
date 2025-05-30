import argparse
import subprocess
import sys
import os
import json

def main():
    parser = argparse.ArgumentParser(description="Run HIL tests using a JSON configuration file.")
    parser.add_argument("test_script", help="Path to the JSON test configuration file. This file should define 'code_to_test', 'input_values', and optionally 'expected_values'.")
    parser.add_argument("--input-values", help="Path to JSON for hardware input actions. Overrides 'input_values' in the test_script JSON.")
    parser.add_argument("--expected-values", help="Path to JSON for expected serial output. Overrides 'expected_values' in the test_script JSON. If not provided here or in JSON, output checking is skipped by main_runner.")
    parser.add_argument("--board", help="Specify the board to use (maps to ST-Link serial number).")
    # Add other arguments that might be useful to expose from hil_tester.main_runner
    parser.add_argument("--serial-port", help="Serial port for STM32 communication.")
    parser.add_argument("--baud-rate", type=int, help="Baud rate for serial communication.")
    parser.add_argument("--skip-flash", action="store_true", help="Skip the flashing step.")
    parser.add_argument("--st-flash-cmd", help="Command for st-flash utility.")
    parser.add_argument("--flash-address", help="Flash memory address for st-flash.")
    parser.add_argument("--gpio-mode", choices=["BCM", "BOARD"], help="GPIO pin numbering mode (BCM or BOARD).")
    parser.add_argument("--receive-timeout", type=int, help="Overall timeout in seconds for receiving serial data.")

    args = parser.parse_args()

    # Validate and parse the JSON test script
    if not os.path.exists(args.test_script):
        print(f"Error: Test configuration file '{args.test_script}' not found.")
        sys.exit(1)

    config_dir = os.path.dirname(os.path.abspath(args.test_script))
    try:
        with open(args.test_script, 'r') as f:
            test_config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON test configuration file '{args.test_script}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading test configuration file '{args.test_script}': {e}")
        sys.exit(1)

    # Determine paths for code_to_test, input_values, and expected_values
    # 1. Firmware path (code_to_test) - must be in JSON
    firmware_path_from_json = test_config.get("code_to_test")
    if not firmware_path_from_json:
        print(f"Error: 'code_to_test' not found in '{args.test_script}'. This is a required field.")
        sys.exit(1)
    actual_firmware_path = firmware_path_from_json if os.path.isabs(firmware_path_from_json) else os.path.normpath(os.path.join(config_dir, firmware_path_from_json))
    if not os.path.exists(actual_firmware_path):
        print(f"Error: Firmware file '{actual_firmware_path}' (from 'code_to_test' in JSON) not found.")
        sys.exit(1)

    # 2. Input values path
    input_values_path_from_json = test_config.get("input_values")
    actual_input_values_path = None
    if args.input_values:
        actual_input_values_path = args.input_values # Assumed relative to CWD or absolute
        if not os.path.exists(actual_input_values_path): # Check existence for CLI provided path
             print(f"Error: Input values file '{actual_input_values_path}' (from --input-values argument) not found.")
             sys.exit(1)
    elif input_values_path_from_json:
        actual_input_values_path = input_values_path_from_json if os.path.isabs(input_values_path_from_json) else os.path.normpath(os.path.join(config_dir, input_values_path_from_json))
        if not os.path.exists(actual_input_values_path):
            print(f"Error: Input values file '{actual_input_values_path}' (from 'input_values' in JSON) not found.")
            sys.exit(1)
    else:
        print(f"Error: 'input_values' not found in '{args.test_script}' and not provided via --input-values. This is required.")
        sys.exit(1)
    
    # 3. Expected values path (optional)
    expected_values_path_from_json = test_config.get("expected_values")
    actual_expected_values_path = None
    if args.expected_values:
        actual_expected_values_path = args.expected_values # Assumed relative to CWD or absolute
        if not os.path.exists(actual_expected_values_path): # Check existence for CLI provided path
            print(f"Error: Expected values file '{actual_expected_values_path}' (from --expected-values argument) not found.")
            sys.exit(1)
    elif expected_values_path_from_json:
        actual_expected_values_path = expected_values_path_from_json if os.path.isabs(expected_values_path_from_json) else os.path.normpath(os.path.join(config_dir, expected_values_path_from_json))
        if not os.path.exists(actual_expected_values_path):
            print(f"Error: Expected values file '{actual_expected_values_path}' (from 'expected_values' in JSON) not found.")
            sys.exit(1)

    # Construct the command for hil_tester.main_runner
    cmd = [
        sys.executable,
        "-m",
        "hil_tester.main_runner",
        "--code-to-test", actual_firmware_path,
        "--input-values", actual_input_values_path,
    ]

    if actual_expected_values_path:
        cmd.extend(["--expected-values", actual_expected_values_path])

    # Add other pass-through arguments
    if args.board:
        cmd.extend(["--stlink-serial", args.board])
    if args.serial_port:
        cmd.extend(["--serial-port", args.serial_port])
    if args.baud_rate:
        cmd.extend(["--baud-rate", str(args.baud_rate)])
    if args.skip_flash:
        cmd.append("--skip-flash")
    if args.st_flash_cmd:
        cmd.extend(["--st-flash-cmd", args.st_flash_cmd])
    if args.flash_address:
        cmd.extend(["--flash-address", args.flash_address])
    if args.gpio_mode:
        cmd.extend(["--gpio-mode", args.gpio_mode])
    if args.receive_timeout:
        cmd.extend(["--receive-timeout", str(args.receive_timeout)])
    
    print(f"Executing command: {' '.join(cmd)}")

    try:
        env = os.environ.copy()
        workspace_root = os.path.dirname(os.path.abspath(__file__))
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = workspace_root + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = workspace_root

        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        print("--- Test Runner Output ---")
        print(result.stdout)
        if result.stderr:
            print("--- Test Runner Errors ---")
            print(result.stderr)
        print("--- Test Run Complete ---")
    except subprocess.CalledProcessError as e:
        print(f"Error running HIL tester (Return Code: {e.returncode}):")
        print("--- stdout ---")
        print(e.stdout)
        print("--- stderr ---")
        print(e.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError: # Catches if sys.executable or -m hil_tester.main_runner fails to find module
        print(f"Error: The Python interpreter '{sys.executable}' or the module 'hil_tester.main_runner' was not found.")
        print("Ensure 'hil_tester' is in your PYTHONPATH or installed, and that 'main_runner.py' exists within it.")
        sys.exit(1)
    except Exception as e: # Catch any other unexpected errors during setup or execution
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 