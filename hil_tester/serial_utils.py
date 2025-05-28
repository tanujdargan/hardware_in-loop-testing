import serial
import time
from signal import signal, SIGINT
from sys import exit as sys_exit # Avoid conflict with other exit vars

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200

class SerialConnection:
    def __init__(self, port=DEFAULT_SERIAL_PORT, baudrate=DEFAULT_BAUD_RATE, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._original_sigint_handler = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Successfully connected to serial port {self.port} at {self.baudrate} baud.")
            # Clear any stale data in buffers
            time.sleep(0.1) # Short delay for connection to establish
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            time.sleep(0.1)
            return True
        except serial.SerialException as e:
            print(f"Error: Could not open serial port {self.port}: {e}")
            self.ser = None
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(f"Serial port {self.port} closed.")
        self.ser = None

    def send_line(self, line_data_str):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write((line_data_str + '\n').encode('utf-8'))
                # print(f"Sent line: {line_data_str}") # Optional: for verbose logging
                return True
            except Exception as e:
                print(f"Error sending line data over serial: {e}")
                return False
        print("Error: Serial port not connected for sending line.")
        return False

    def send_bytes(self, byte_data):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(byte_data)
                # print(f"Sent bytes: {byte_data.hex() if isinstance(byte_data, bytes) else byte_data}") # Optional
                return True
            except Exception as e:
                print(f"Error sending byte data over serial: {e}")
                return False
        print("Error: Serial port not connected for sending bytes.")
        return False

    def read_line(self, timeout_override=None):
        if self.ser and self.ser.is_open:
            original_timeout = self.ser.timeout
            if timeout_override is not None:
                self.ser.timeout = timeout_override
            
            try:
                line = self.ser.readline()
                if timeout_override is not None: # Restore original timeout if it was changed
                    self.ser.timeout = original_timeout

                if line:
                    return line.decode('utf-8', errors='replace').strip()
                return None # Timeout or empty line
            except Exception as e:
                print(f"Error reading line from serial: {e}")
                if timeout_override is not None:
                    self.ser.timeout = original_timeout
                return None
        print("Error: Serial port not connected for reading.")
        return None

    def read_all_lines(self, overall_timeout_seconds=5, stop_condition_line=None, idle_timeout_seconds=1):
        """
        Reads lines until an overall timeout, a stop condition line is met,
        or no new data arrives for idle_timeout_seconds.
        """
        if not (self.ser and self.ser.is_open):
            print("Error: Serial port not connected for reading.")
            return []

        lines_received = []
        start_time = time.time()
        last_data_time = time.time()

        while (time.time() - start_time) < overall_timeout_seconds:
            if (time.time() - last_data_time) > idle_timeout_seconds :
                # print("Idle timeout reached.") # Optional: for debugging
                break

            line = self.read_line(timeout_override=0.05) # Short poll timeout
            if line is not None: # Check for not None, as empty string is False but could be valid after strip
                if line: # Only append non-empty lines after stripping
                    lines_received.append(line)
                    # print(f"Received line: {line}") # Optional: verbose logging
                last_data_time = time.time() # Reset idle timer on any data (even if just newline)
                if stop_condition_line and stop_condition_line == line:
                    print(f"Stop condition line '{stop_condition_line}' met.")
                    break
            # No else needed here, just continue polling if line is None (short timeout occurred)

        if not lines_received:
            print(f"No lines received within the overall timeout ({overall_timeout_seconds}s) or idle timeout ({idle_timeout_seconds}s).")
        return lines_received

    def __enter__(self):
        # Setup custom SIGINT handler
        self._original_sigint_handler = signal(SIGINT, self._graceful_exit_handler)
        if not self.connect():
            # Propagate error if connection fails, so 'with' block might not execute
            raise ConnectionError(f"Failed to connect to serial port {self.port}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        # Restore original SIGINT handler
        if self._original_sigint_handler:
            signal(SIGINT, self._original_sigint_handler)

    def _graceful_exit_handler(self, sig, frame):
        print("\nSIGINT or CTRL-C detected. Closing serial port and exiting.")
        self.disconnect()
        sys_exit(1) # Exit with an error code 