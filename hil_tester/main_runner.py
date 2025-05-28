import argparse
import os
import sys
import time
import json

# Adjust imports for the new directory structure if these files are also moved
# For now, assume they will be in the same directory or Python path is handled.
from .stm32_flasher import flash_firmware
from .pin_emulator import emulate_hw_pins_from_file, GPIOControllerError
from .serial_receiver import SerialReceiver, DEFAULT_SERIAL_PORT, DEFAULT_BAUD_RATE, SerialReceiverError
from .gpio_controller import GPIOController, GPIOControllerError as GPIOInitError
from .output_checker import check_output

def main():
    parser = argparse.ArgumentParser(
        description="HIL Test Runner: Flashes STM32, emulates inputs, receives serial, checks output.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--code-to-test", required=True, help="Path to STM32 firmware (.bin/.hex).")
    parser.add_argument("--input-values", required=True, help="Path to JSON for hardware input actions (e.g., GPIO toggle).")
    parser.add_argument("--expected-values", help="Path to JSON for expected serial output. If not provided, output checking is skipped.")

    parser.add_argument("--serial-port", default=DEFAULT_SERIAL_PORT, help="Serial port for STM32 communication.")
    parser.add_argument("--baud-rate", type=int, default=DEFAULT_BAUD_RATE, help="Baud rate for serial communication.")
    parser.add_argument("--skip-flash", action="store_true", help="Skip the flashing step.")
    parser.add_argument("--st-flash-cmd", default="st-flash", help="Command for st-flash utility.")
    parser.add_argument("--flash-address", default="0x08000000", help="Flash memory address for st-flash.")
    parser.add_argument("--stlink-serial", default=None, help="ST-Link programmer serial number. If not provided, st-flash will use the first one found.")
    parser.add_argument("--gpio-mode", default="BCM", choices=["BCM", "BOARD"], help="GPIO pin numbering mode (BCM or BOARD).")
    parser.add_argument("--receive-timeout", type=int, default=10, help="Overall timeout in seconds for receiving serial data.")

    args = parser.parse_args()

    print("--- HIL Test Run Start ---")
    print(f"Firmware: {args.code_to_test}")
    print(f"Input Actions: {args.input_values}")
    if args.expected_values:
        print(f"Expected Values: {args.expected_values}")
    else:
        print("Expected Values: Not provided, output checking will be skipped.")
    print(f"Serial: {args.serial_port} @ {args.baud_rate}bps")
    if args.stlink_serial:
        print(f"ST-Link Serial: {args.stlink_serial}")
    print(f"GPIO Mode: {args.gpio_mode}")

    script_ran_to_completion = False
    test_passed = False

    if not args.skip_flash:
        print("\n--- Step 1: Flashing STM32 ---")
        if not os.path.exists(args.code_to_test):
            print(f"Fatal Error: Firmware file '{args.code_to_test}' not found.")
            sys.exit(1)
        try:
            if not flash_firmware(args.code_to_test, stlink_command=args.st_flash_cmd, address=args.flash_address, serial_number=args.stlink_serial):
                print("STM32 flashing reported failure. Aborting.")
                sys.exit(1)
            print("Flashing reported success. Delaying for STM32 boot...")
            time.sleep(3)
        except Exception as e:
            print(f"Fatal Error during flashing: {e}")
            sys.exit(1)
    else:
        print("\n--- Step 1: Flashing STM32 (Skipped) ---")

    received_data = None

    try:
        with GPIOController(mode_str=args.gpio_mode) as gpio_ctrl:
            print("\n--- Step 2: Emulating Hardware Pin Inputs ---")
            input_actions_config = emulate_hw_pins_from_file(args.input_values, gpio_ctrl)
            if input_actions_config is None:
                print("Hardware pin input emulation failed critically. Aborting.")
                sys.exit(1)
            
            print("Pin emulation sequence complete. Waiting briefly for STM32 to process...")
            time.sleep(1)

            print("\n--- Step 3: Receiving Output from STM32 (via Serial) ---")
            with SerialReceiver(port=args.serial_port, baudrate=args.baud_rate) as ser_rcv:
                if not ser_rcv.is_connected():
                     print(f"Fatal Error: Failed to connect to serial port {args.serial_port}. Aborting.")
                     sys.exit(1)

                reception_mode_for_receiver = "lines"
                if args.expected_values and os.path.exists(args.expected_values):
                    try:
                        with open(args.expected_values, 'r') as f_exp:
                            expected_config_for_mode = json.load(f_exp)
                        reception_mode_for_receiver = expected_config_for_mode.get("reception_mode", "lines")
                        print(f"Using reception mode '{reception_mode_for_receiver}' from expected_values file.")
                    except Exception as e:
                        print(f"Warning: Could not read reception_mode from {args.expected_values}: {e}. Defaulting to 'lines'.")

                print(f"Listening for serial data (mode: {reception_mode_for_receiver}) for up to {args.receive_timeout} seconds...")
                received_data = ser_rcv.receive_data(
                    mode=reception_mode_for_receiver,
                    overall_timeout_s=args.receive_timeout,
                    idle_timeout_s=max(1, args.receive_timeout // 2)
                )

        print("\n--- Step 4: Output Checking ---")
        if args.expected_values:
            if not os.path.exists(args.expected_values):
                print(f"Warning: Expected values file '{args.expected_values}' not found. Skipping output check.")
                test_passed = True
            else:
                if received_data is None:
                    print("No data was received from STM32. Output checking cannot proceed.")
                    test_passed = False
                else:
                    test_passed = check_output(received_data, args.expected_values, input_actions_config)
        else:
            print("No expected values file provided. Output checking skipped.")
            if received_data is not None:
                print("Received some data and no expectations defined, considering script part successful.")
                test_passed = True
            else:
                print("No data received and no expectations defined.")
                test_passed = False

        script_ran_to_completion = True

    except GPIOInitError as e:
        print(f"Fatal GPIO Initialization Error: {e}")
    except GPIOControllerError as e:
        print(f"Fatal GPIO Emulation Error: {e}")
    except SerialReceiverError as e:
        print(f"Fatal Serial Communication Error: {e}")
    except ConnectionError as e:
        print(f"Fatal Connection Error: {e}")
    except Exception as e:
        print(f"An Unexpected Fatal Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n--- HIL Test Run End ---")
        if script_ran_to_completion:
            if test_passed:
                print("HIL Test Result: PASSED")
                sys.exit(0)
            else:
                print("HIL Test Result: FAILED (Output did not match expected or other test failure)")
                sys.exit(1)
        else:
            print("Script did not complete due to an error before test evaluation.")
            sys.exit(2)

if __name__ == "__main__":
    main() 