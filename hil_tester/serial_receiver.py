import serial
import time
import json
from signal import signal, SIGINT
from sys import exit as sys_exit

DEFAULT_SERIAL_PORT = "/dev/ttyACM0"
DEFAULT_BAUD_RATE = 115200

class SerialReceiverError(Exception):
    """Custom exception for SerialReceiver errors."""
    pass

class SerialReceiver:
    def __init__(self, port=DEFAULT_SERIAL_PORT, baudrate=DEFAULT_BAUD_RATE, timeout=1):
        if not port or not isinstance(port, str):
            raise SerialReceiverError(f"Invalid serial port specified: {port}. Must be a string (e.g., '/dev/ttyACM0').")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout # Default timeout for individual readline calls
        self.ser = None
        self._original_sigint_handler = None
        print(f"SerialReceiver initialized for port {port}, baudrate {baudrate}")


    def connect(self):
        if self.ser and self.ser.is_open:
            print("SerialReceiver Warning: Already connected. Closing existing connection first.")
            self.disconnect()
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"SerialReceiver: Successfully connected to {self.port}.")
            # It's good practice to wait briefly and clear buffers after opening
            time.sleep(0.2) # Increased slightly
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
            return True
        except serial.SerialException as e:
            # This exception is quite broad, can be port not found, permission denied, etc.
            raise SerialReceiverError(f"Could not open serial port '{self.port}': {e}")
        except Exception as e: # Catch any other unexpected error during connection
            raise SerialReceiverError(f"Unexpected error connecting to serial port '{self.port}': {e}")


    def disconnect(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                print(f"SerialReceiver: Port {self.port} closed.")
            except Exception as e:
                print(f"SerialReceiver Warning: Error closing serial port {self.port}: {e}")
        self.ser = None # Ensure it's None even if close fails

    def read_line(self, timeout_override=None) -> str | None:
        if not self.is_connected():
            # This can be very noisy if called in a loop when not connected.
            # Consider raising an error or ensuring connect is called first.
            # For now, returning None.
            return None 
        
        original_timeout = self.ser.timeout
        actual_timeout = timeout_override if timeout_override is not None else self.ser.timeout
        
        try:
            if timeout_override is not None: # Temporarily set timeout if overridden
                self.ser.timeout = actual_timeout
            
            line_bytes = self.ser.readline() # This will block up to 'actual_timeout'
            
            if line_bytes:
                return line_bytes.decode('utf-8', errors='replace').strip()
            return "" # Timeout occurred, readline returned empty bytes
        except serial.SerialException as e: # E.g. device disconnected
            raise SerialReceiverError(f"SerialException while reading line from {self.port}: {e}")
        except Exception as e:
            raise SerialReceiverError(f"Unexpected error reading line from {self.port}: {e}")
        finally:
            if timeout_override is not None and self.is_connected(): # Restore original timeout
                try:
                    self.ser.timeout = original_timeout
                except Exception: # e.g. if port closed due to error during read
                    pass


    def receive_data(self, mode="lines", overall_timeout_s=5, stop_condition_line=None, idle_timeout_s=1) -> list[str] | dict | str:
        """
        Receives data. For simplified goal, mode='lines' or 'raw_stream' is fine.
        Returns empty list/dict/string if no data or error that doesn't halt execution.
        Raises SerialReceiverError for critical issues.
        """
        if not self.is_connected():
            raise SerialReceiverError("Not connected. Cannot receive data.")

        print(f"SerialReceiver: Receiving data (Mode: {mode}, OverallTimeout: {overall_timeout_s}s, StopLine: '{stop_condition_line}', IdleTimeout: {idle_timeout_s}s)")
        
        buffer = ""
        lines_received = []
        start_time = time.time()
        last_data_time = time.time()

        try:
            while (time.time() - start_time) < overall_timeout_s:
                if (time.time() - last_data_time) > idle_timeout_s:
                    if mode == "json_object" and buffer.count('{') > buffer.count('}'): # Still waiting for json to complete
                         pass # Continue if it looks like we are mid-JSON
                    else:
                        print(f"SerialReceiver: Idle timeout ({idle_timeout_s}s) reached.")
                        break

                bytes_available = self.ser.in_waiting
                if bytes_available > 0:
                    data_chunk = self.ser.read(bytes_available).decode('utf-8', errors='replace')
                    if data_chunk: # If actual data was read
                        buffer += data_chunk
                        last_data_time = time.time()
                else: # No data immediately available
                    time.sleep(0.05) # Short poll delay

                if mode == "lines":
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        processed_line = line.strip() # Strip here
                        # if processed_line: # Only add if not empty after strip
                        lines_received.append(processed_line) # Add even if empty after strip, if newline was there
                        print(f"  Line Rcvd: \"{processed_line}\"")
                        if stop_condition_line and processed_line == stop_condition_line:
                            print("  Stop condition line met.")
                            return lines_received
                elif mode == "json_object":
                    # Try to parse if buffer looks like it might contain a complete JSON object
                    # This is heuristic. A robust solution requires framing or a streaming parser.
                    if buffer.strip().startswith('{') and buffer.strip().endswith('}'):
                        try:
                            json_obj = json.loads(buffer.strip())
                            print(f"  JSON Object Rcvd & Parsed. Root type: {type(json_obj).__name__}")
                            return json_obj
                        except json.JSONDecodeError:
                             pass # Not a complete JSON object yet, or invalid
                # For "raw_stream", we just accumulate.
            
            # Loop ended (timeout or other break)
            if mode == "lines":
                if buffer.strip(): # Process any remaining part of the buffer
                    lines_received.append(buffer.strip())
                    print(f"  Line Rcvd (final buffer): \"{buffer.strip()}\"")
                return lines_received
            elif mode == "json_object":
                print("SerialReceiver: Timeout or end of data for JSON object. Final parse attempt.")
                try:
                    json_obj = json.loads(buffer.strip()) # Try to parse the whole stripped buffer
                    print(f"  JSON Object Rcvd & Parsed (final attempt). Root type: {type(json_obj).__name__}")
                    return json_obj
                except json.JSONDecodeError:
                    print(f"SerialReceiver: Final JSON parse attempt failed. Buffer content: '{buffer.strip()}'")
                    # Return an error structure or the raw buffer
                    return {"error": "invalid_or_incomplete_json", "buffer": buffer.strip()}
            elif mode == "raw_stream":
                return buffer.strip() # Return the full accumulated buffer, stripped

        except serial.SerialException as e:
            raise SerialReceiverError(f"SerialException during data reception from {self.port}: {e}")
        except Exception as e:
            raise SerialReceiverError(f"Unexpected error during data reception from {self.port}: {e}")
        
        # Fallback return for modes if loop finishes without specific return
        if mode == "lines": return lines_received
        if mode == "json_object": return {"error": "timeout_before_valid_json", "buffer": buffer.strip()}
        if mode == "raw_stream": return buffer.strip()
        return "" # Default for unknown mode or if nothing specific happened


    def is_connected(self):
        return self.ser and self.ser.is_open

    def __enter__(self):
        # SIGINT handling setup
        self._original_sigint_handler = signal(SIGINT, self._graceful_exit_handler_sigint)
        try:
            self.connect()
        except SerialReceiverError as e:
            # Restore original SIGINT handler if connect fails before __exit__ is called
            if self._original_sigint_handler:
                signal(SIGINT, self._original_sigint_handler)
            raise # Re-raise the connection error
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        # Restore original SIGINT handler
        if self._original_sigint_handler:
            signal(SIGINT, self._original_sigint_handler)
            self._original_sigint_handler = None # Avoid multiple restores if __exit__ called again

    def _graceful_exit_handler_sigint(self, sig, frame):
        print("\nSIGINT or CTRL-C detected by SerialReceiver. Closing port...")
        # self.disconnect() # __exit__ will handle this.
        # To ensure exit, and if __exit__ isn't guaranteed (e.g. error in __enter__ before ser is set)
        if self.ser and self.ser.is_open:
            try: self.ser.close()
            except: pass # Ignore errors on close during critical exit
        print("Serial port closed due to SIGINT. Exiting script.")
        sys_exit(1) 