import serial
import time
import os
import json # Assuming test cases might be defined in JSON format
import subprocess
from signal import signal, SIGINT
from sys import exit

# --- Configuration ---
# Serial port parameters, taken from your provided scripts (e.g., read_serial.py, recieving.py)
SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200
# Path to the cloned test repository on the RPi
TEST_REPO_PATH = "./hardware_in-loop-testing/test_repo" # Adjust as needed
TESTS_SUBFOLDER = "tests" # Subfolder within TEST_REPO_PATH containing actual test definitions/scripts

# Global serial connection object
ser = None

# --- Graceful Exit Handler ---
def graceful_exit_handler(signal_received, frame):
    print('\nSIGINT or CTRL-C detected. Exiting gracefully.')
    if ser and ser.is_open:
        ser.close()
        print('Serial port closed.')
    exit(0)

# --- Core Functions ---

def initialize_serial():
    """Initializes the serial connection to the STM32 board."""
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Serial port {SERIAL_PORT} opened successfully at {BAUD_RATE} baud.")
        time.sleep(2) # Wait for the connection to establish
    except serial.SerialException as e:
        print(f"Error opening serial port {SERIAL_PORT}: {e}")
        exit(1)

def pull_latest_code(repo_path):
    """
    Pulls the latest code from the Git repository.
    Assumes Git is configured on the RPi and the script has necessary permissions.
    The README.md mentions that the workflow on the yaml file starts when a push is made to main.
    This function can be triggered as part of that workflow or run manually.
    """
    print(f"Pulling latest code from repository at {repo_path}...")
    try:
        # Ensure we are in the repository directory
        original_dir = os.getcwd()
        os.chdir(repo_path)
        subprocess.run(["git", "pull"], check=True)
        os.chdir(original_dir)
        print("Successfully pulled latest code.")
    except subprocess.CalledProcessError as e:
        print(f"Error pulling repository: {e}")
        # Potentially fall back to using existing code or handle error
    except FileNotFoundError:
        print(f"Error: Git repository path not found at {repo_path}")

def find_test_files(test_data_path):
    """
    Finds test definition files (e.g., .json, .py for test logic) in the specified path.
    This function will need to be adapted based on how test cases are defined.
    """
    print(f"Looking for test files in {test_data_path}...")
    test_files = []
    for root, _, files in os.walk(test_data_path):
        for file in files:
            # Example: looking for JSON files defining tests or Python scripts
            if file.endswith(".json") or file.startswith("test_") and file.endswith(".py"):
                test_files.append(os.path.join(root, file))
    print(f"Found test files: {test_files}")
    return test_files

def execute_test_case(test_file_path):
    """
    Executes a single test case.
    This function will be a primary integration point for scripts developed by others.
    """
    print(f"\n--- Executing Test Case: {os.path.basename(test_file_path)} ---")

    # 1. Read Test Definition (Example: from a JSON file)
    # This part needs to be adapted based on your test file format.
    # For example, a test file might specify input values to send,
    # or parameters for the "emulation" script.
    try:
        with open(test_file_path, 'r') as f:
            test_config = json.load(f) # Assuming JSON for this example
        print(f"Loaded test configuration: {test_config}")
    except Exception as e:
        print(f"Error loading test configuration from {test_file_path}: {e}")
        return False

    # 2. Emulate Values (Placeholder - to be implemented by others)
    # This section would call the script/logic responsible for emulation.
    # It might involve sending specific commands/data to the STM32.
    print("Emulating values (placeholder)...")
    # Example:
    # emulated_inputs = test_config.get("inputs_to_emulate", [])
    # for inp in emulated_inputs:
    #     if ser and ser.is_open:
    #         ser.write(f"{inp}\n".encode('utf-8'))
    #         print(f"Sent emulated input: {inp}")
    #         time.sleep(0.1) # Give STM32 time to process
    # This part is highly dependent on how "emulation" is defined for your project.

    # 3. Receive Values over Serial
    # Leveraging logic similar to your 'read_serial.py' or 'recieving.py'
    print("Attempting to receive values from STM32 over serial...")
    received_data_lines = []
    max_receive_time_seconds = 10 # Timeout for receiving data
    start_time = time.time()
    
    # It's important that the STM32 code (like your test1.c, but more functional)
    # is programmed to send data back over serial in a recognizable format.
    # For instance, it might send data ending with a newline.
    
    if not ser or not ser.is_open:
        print("Serial port not available for receiving.")
        return False

    try:
        while (time.time() - start_time) < max_receive_time_seconds:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"Received: {line}")
                    received_data_lines.append(line)
                    # Add logic here if a specific "end of message" signal is expected
                    # For example, if the STM32 sends "TEST_COMPLETE"
                    if "TEST_COMPLETE" in line: # Example break condition
                        break 
            else:
                time.sleep(0.05) # Small delay to avoid busy-waiting

        if not received_data_lines:
            print("No data received from STM32 within the timeout period.")

    except Exception as e:
        print(f"Error during serial communication: {e}")
        return False

    # 4. Confirm Tests (Placeholder - to be implemented by others)
    # This section would call the script/logic responsible for test confirmation.
    # It would compare received_data_lines against expected_outputs from test_config.
    print("Confirming test results (placeholder)...")
    # Example:
    # expected_outputs = test_config.get("expected_outputs", [])
    # success = True
    # if len(received_data_lines) != len(expected_outputs):
    #     success = False
    # else:
    #     for i, received_line in enumerate(received_data_lines):
    #         if received_line != expected_outputs[i]: # Adjust comparison logic as needed
    #             print(f"Mismatch: Expected '{expected_outputs[i]}', Got '{received_line}'")
    #             success = False
    #             break
    # if success:
    #     print("Test PASSED!")
    # else:
    #     print("Test FAILED.")
    # return success
    
    # For now, we'll just simulate a pass
    print(f"--- Test Case {os.path.basename(test_file_path)} Finished ---")
    return True # Placeholder

# --- Main Execution ---
if __name__ == "__main__":
    # Register the signal handler for graceful exit
    signal(SIGINT, graceful_exit_handler)

    # Initialize serial connection
    initialize_serial()

    # (Optional) Pull latest code from the repository
    # The README.md implies this might be handled by a GitHub Actions workflow
    # pull_latest_code(TEST_REPO_PATH)

    # Define the path to your test definitions/scripts
    # This assumes your tests are in a subfolder like 'tests' within the 'test_repo'
    # The structure you provided is: hardware_in-loop-testing/tests and hardware_in-loop-testing/test_repo
    # Let's assume functional tests scripts or definitions are in hardware_in-loop-testing/tests
    path_to_individual_tests = os.path.join(os.path.dirname(TEST_REPO_PATH), TESTS_SUBFOLDER)


    if not os.path.isdir(path_to_individual_tests):
        print(f"Error: Test data path {path_to_individual_tests} not found. Please check TEST_REPO_PATH and TESTS_SUBFOLDER.")
        if ser and ser.is_open:
            ser.close()
        exit(1)

    test_files = find_test_files(path_to_individual_tests)

    if not test_files:
        print(f"No test files found in {path_to_individual_tests}. Exiting.")
    else:
        print(f"\nFound {len(test_files)} test(s). Starting test execution...")
        for test_file in test_files:
            execute_test_case(test_file)
            # Add a small delay between tests if needed
            time.sleep(1)

    # Clean up
    if ser and ser.is_open:
        ser.close()
        print("Serial port closed at the end of testing.")
    print("\nAll tests completed.") 