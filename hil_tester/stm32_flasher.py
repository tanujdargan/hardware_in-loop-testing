import subprocess
import os

DEFAULT_STLINK_FLASH_COMMAND = "st-flash"
DEFAULT_FLASH_ADDRESS = "0x08000000"

def flash_firmware(firmware_path, stlink_command=DEFAULT_STLINK_FLASH_COMMAND, address=DEFAULT_FLASH_ADDRESS, serial_number=None):
    """
    Flashes the STM32 with the provided firmware file using st-flash.
    Args:
        firmware_path (str): Path to the .bin or .hex firmware file.
        stlink_command (str): The st-flash command (e.g., 'st-flash').
        address (str): The memory address to write to (e.g., '0x08000000').
        serial_number (str, optional): ST-Link programmer serial number. Defaults to None.
    Returns:
        bool: True if flashing was successful, False otherwise.
    """
    if not os.path.exists(firmware_path):
        print(f"Error: Firmware file not found at '{firmware_path}'")
        return False

    command_base = [stlink_command]
    if serial_number:
        command_base.extend(["--serial", serial_number])
    
    command = command_base + ["write", firmware_path, address]
    
    # Also prepare reset command if serial number is used
    reset_command = [stlink_command]
    if serial_number:
        reset_command.extend(["--serial", serial_number])
    reset_command.append("reset")

    print(f"Attempting to flash STM32 with command: {' '.join(command)}")
    try:
        process = subprocess.run(command, check=True, capture_output=True, text=True)
        print("STM32 Flashing Output:")
        if process.stdout:
            print("STDOUT:\n" + process.stdout)
        if process.stderr:
             print("STDERR:\n" + process.stderr)
        
        if "verify success" in process.stderr.lower() or \
           "flash written and verified successfully" in process.stderr.lower() or \
           (process.returncode == 0 and "error" not in process.stderr.lower()):
            print("Firmware successfully flashed to STM32.")
            # Attempt reset after successful flash
            try:
                print(f"Attempting to reset STM32 with command: {' '.join(reset_command)}")
                subprocess.run(reset_command, check=True, capture_output=True, text=True)
                print("STM32 reset successfully.")
            except subprocess.CalledProcessError as e_reset:
                print(f"Error during STM32 reset after flashing: {e_reset.stderr}")
                # Decide if this is critical; for now, flashing itself was a success.
            return True
        else:
            print("Warning: st-flash completed but success message not definitively found in output.")
            if process.returncode == 0 and "error" not in process.stderr.lower():
                print("Interpreting as success due to zero return code and no explicit error.")
                return True
            print("Flashing may have failed or had issues. Review output.")
            return False

    except subprocess.CalledProcessError as e:
        print("Error during STM32 flashing operation:")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"Return code: {e.returncode}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: Flashing command '{stlink_command}' not found. Is stlink-tools installed and in PATH?")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during flashing: {e}")
        return False 