import time

# Attempt to import RPi.GPIO and handle cases where it might not be available
try:
    import RPi.GPIO as GPIO
    HAS_GPIO_LIB = True
except ImportError:
    print("---------------------------------------------------------------------")
    print("Warning: RPi.GPIO library not found. GPIO operations will be mocked.")
    print("Ensure RPi.GPIO is installed on a Raspberry Pi for actual hardware control (e.g., sudo apt-get install python3-rpi.gpio)")
    print("---------------------------------------------------------------------")
    HAS_GPIO_LIB = False
    # Mock GPIO class for development on non-RPi systems
    class MockGPIO:
        BCM = "BCM_MODE"
        BOARD = "BOARD_MODE"
        OUT = "OUTPUT_MODE"
        IN = "INPUT_MODE"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        
        def __init__(self):
            self._mode = None
            self._pin_setups = {} # pin: {"direction": OUT/IN, "value": HIGH/LOW, "pud": PUD_UP/DOWN}
            self._warnings_on = True # Corresponds to GPIO.setwarnings(True)

        def setmode(self, mode):
            self._mode = mode
            print(f"MockGPIO: Mode set to {self._mode}")

        def setup(self, pin, direction, initial=None, pull_up_down=None):
            if pin in self._pin_setups and self._warnings_on:
                 print(f"MockGPIO Warning: Pin {pin} already setup. Overwriting.")
            self._pin_setups[pin] = {"direction": direction}
            if direction == self.OUT:
                value_to_set = initial if initial is not None else self.LOW
                self._pin_setups[pin]["value"] = value_to_set
                print(f"MockGPIO: Pin {pin} setup as OUTPUT, initial value {('HIGH' if value_to_set == self.HIGH else 'LOW')}")
            elif direction == self.IN:
                self._pin_setups[pin]["pud"] = pull_up_down
                # Simplistic mock: if pull-up, assume high, else low if pull-down or no pull
                self._pin_setups[pin]["value"] = self.HIGH if pull_up_down == self.PUD_UP else self.LOW
                print(f"MockGPIO: Pin {pin} setup as INPUT, pull_up_down {pull_up_down}, mocked value {('HIGH' if self._pin_setups[pin]['value'] == self.HIGH else 'LOW')}")

        def output(self, pin, value):
            if pin not in self._pin_setups or self._pin_setups[pin].get("direction") != self.OUT:
                # RPi.GPIO raises RuntimeError if not setup as OUT
                raise RuntimeError(f"MockGPIO: Pin {pin} not setup as OUTPUT or not setup at all.")
            self._pin_setups[pin]["value"] = value
            print(f"MockGPIO: Pin {pin} set to {('HIGH' if value == self.HIGH else 'LOW')}")

        def input(self, pin):
            if pin not in self._pin_setups or self._pin_setups[pin].get("direction") != self.IN:
                 # RPi.GPIO raises RuntimeError if not setup as IN
                raise RuntimeError(f"MockGPIO: Pin {pin} not setup as INPUT or not setup at all.")
            val = self._pin_setups[pin].get("value", self.LOW) # Default to LOW
            print(f"MockGPIO: Reading from pin {pin}, returning {('HIGH' if val == self.HIGH else 'LOW')}")
            return val

        def cleanup(self, pin_or_channel_list=None):
            if pin_or_channel_list is None: # cleanup all
                self._pin_setups.clear()
                print("MockGPIO: Cleaned up all channels.")
            elif isinstance(pin_or_channel_list, int): # cleanup single pin
                if pin_or_channel_list in self._pin_setups:
                    del self._pin_setups[pin_or_channel_list]
                print(f"MockGPIO: Cleaned up pin {pin_or_channel_list}.")
            elif isinstance(pin_or_channel_list, list): # cleanup list of pins
                 for p in pin_or_channel_list:
                     if p in self._pin_setups: del self._pin_setups[p]
                 print(f"MockGPIO: Cleaned up pins {pin_or_channel_list}.")


        def setwarnings(self, state_bool):
            self._warnings_on = state_bool # True means warnings are on (like GPIO.setwarnings(True))
            print(f"MockGPIO: Warnings set to {state_bool}")
        
        def getmode(self):
            return self._mode

    GPIO = MockGPIO() # Replace actual GPIO with mock if lib not found

class GPIOControllerError(Exception):
    """Custom exception for GPIOController errors."""
    pass

class GPIOController:
    def __init__(self, mode_str="BCM"):
        self.is_mocked = not HAS_GPIO_LIB
        if self.is_mocked:
            print("GPIOController: Initializing with Mock RPi.GPIO.")
        
        try:
            # Set warnings to False to prevent console messages for re-setup, etc.
            # We will handle errors explicitly.
            GPIO.setwarnings(False) 
            
            current_gpio_mode = GPIO.getmode() # Can be None if not set, or BCM/BOARD/etc.
            
            target_mode = None
            if mode_str.upper() == "BCM":
                target_mode = GPIO.BCM
            elif mode_str.upper() == "BOARD":
                target_mode = GPIO.BOARD
            else:
                raise GPIOControllerError(f"Invalid GPIO mode '{mode_str}'. Choose 'BCM' or 'BOARD'.")

            # Only call setmode if it hasn't been set or is different
            # RPi.GPIO raises an error if setmode is called multiple times with different modes
            # or even the same mode after pins are in use. It's best to set it once.
            # However, for simplicity in a script that might be run multiple times or re-instantiate this,
            # we might need a strategy. The safest is to clean up fully on exit.
            # For now, if a mode is set and different, it's an issue. If no mode set, we set it.
            if current_gpio_mode is None:
                GPIO.setmode(target_mode)
                print(f"GPIOController: Mode set to {mode_str.upper()}")
            elif current_gpio_mode != target_mode:
                 raise GPIOControllerError(
                    f"GPIO mode conflict. Current mode is {current_gpio_mode}, "
                    f"requested {target_mode}. Cleanup GPIO before changing mode."
                )
            else:
                print(f"GPIOController: Mode already set to {mode_str.upper()}")

        except Exception as e: # Catch errors from RPi.GPIO's setmode/getmode or our logic
            raise GPIOControllerError(f"Failed to initialize GPIO controller mode: {e}")

        self.pin_configs = {} # pin: {"direction": "output"/"input"}


    def _validate_pin(self, pin):
        if not isinstance(pin, int) or not (0 <= pin <= 40): # Basic check for RPi pins
            raise GPIOControllerError(f"Invalid pin number {pin}. Must be an integer (e.g., 0-40).")

    def setup_pin_direction(self, pin, direction_str, initial_str=None, pull_up_down_str=None):
        self._validate_pin(pin)
        print(f"GPIOController: Setting up pin {pin} as {direction_str.upper()}")
        
        try:
            direction = GPIO.OUT if direction_str.lower() == "output" else GPIO.IN
            
            initial_val = None
            if direction_str.lower() == "output" and initial_str:
                initial_val = GPIO.HIGH if initial_str.lower() == "high" else GPIO.LOW

            pud = None
            if direction_str.lower() == "input" and pull_up_down_str:
                if pull_up_down_str.lower() == "pull_up": pud = GPIO.PUD_UP
                elif pull_up_down_str.lower() == "pull_down": pud = GPIO.PUD_DOWN
                # else GPIO.PUD_OFF is the default for RPi.GPIO if no pull_up_down is specified

            if direction == GPIO.OUT:
                if initial_val is not None:
                    GPIO.setup(pin, direction, initial=initial_val)
                else:
                    GPIO.setup(pin, direction) 
            elif direction == GPIO.IN:
                if pud is not None:
                    GPIO.setup(pin, direction, pull_up_down=pud)
                else:
                    GPIO.setup(pin, direction)
            
            self.pin_configs[pin] = {"direction": direction_str.lower()}
            print(f"GPIOController: Pin {pin} successfully set up as {direction_str.upper()}.")

        except RuntimeError as e: # RPi.GPIO specific errors (e.g., pin already in use differently)
            raise GPIOControllerError(f"RPi.GPIO RuntimeError setting up pin {pin}: {e}")
        except Exception as e: # Other unexpected errors
            raise GPIOControllerError(f"Unexpected error setting up pin {pin}: {e}")


    def set_pin_output(self, pin, value_str):
        self._validate_pin(pin)
        if self.pin_configs.get(pin, {}).get("direction") != "output":
            raise GPIOControllerError(f"Pin {pin} not configured as output. Call setup_pin_direction first.")
        
        try:
            value = GPIO.HIGH if value_str.lower() == "high" else GPIO.LOW
            GPIO.output(pin, value)
            print(f"GPIOController: Pin {pin} set to {value_str.upper()}")
        except RuntimeError as e:
            raise GPIOControllerError(f"RPi.GPIO RuntimeError setting output for pin {pin}: {e}")
        except Exception as e:
            raise GPIOControllerError(f"Unexpected error setting output for pin {pin}: {e}")

    def read_pin_input(self, pin):
        self._validate_pin(pin)
        if self.pin_configs.get(pin, {}).get("direction") != "input":
            raise GPIOControllerError(f"Pin {pin} not configured as input. Call setup_pin_direction first.")

        try:
            value = GPIO.input(pin)
            state = "HIGH" if value == GPIO.HIGH else "LOW"
            print(f"GPIOController: Pin {pin} read as {state}")
            return state
        except RuntimeError as e:
            raise GPIOControllerError(f"RPi.GPIO RuntimeError reading input from pin {pin}: {e}")
        except Exception as e:
            raise GPIOControllerError(f"Unexpected error reading input from pin {pin}: {e}")


    def pulse_pin_output(self, pin, duration_ms, pulse_state_str="high", initial_state_str=None):
        self._validate_pin(pin)
        if self.pin_configs.get(pin, {}).get("direction") != "output":
             raise GPIOControllerError(f"Pin {pin} not configured for output (for pulse). Call setup_pin_direction first.")

        try:
            active_state = GPIO.HIGH if pulse_state_str.lower() == "high" else GPIO.LOW
            
            if initial_state_str:
                inactive_state = GPIO.HIGH if initial_state_str.lower() == "high" else GPIO.LOW
            else: 
                inactive_state = GPIO.LOW if active_state == GPIO.HIGH else GPIO.HIGH

            # Set to initial/inactive state first
            GPIO.output(pin, inactive_state)
            time.sleep(0.001) # Small delay to ensure state settles

            # Perform pulse
            GPIO.output(pin, active_state)
            print(f"GPIOController: Pin {pin} pulsed to {pulse_state_str.upper()} for {duration_ms}ms (from {'HIGH' if inactive_state == GPIO.HIGH else 'LOW'})")
            time.sleep(duration_ms / 1000.0)
            GPIO.output(pin, inactive_state)
            print(f"GPIOController: Pin {pin} pulse ended, returned to {'HIGH' if inactive_state == GPIO.HIGH else 'LOW'}")

        except RuntimeError as e:
            raise GPIOControllerError(f"RPi.GPIO RuntimeError during pulse for pin {pin}: {e}")
        except Exception as e:
            raise GPIOControllerError(f"Unexpected error during pulse for pin {pin}: {e}")

    def cleanup(self, pin=None):
        action_taken = False
        try:
            if not self.is_mocked: # Only attempt real cleanup if not mocked
                if pin is None: # Cleanup all pins used by this controller instance
                    if self.pin_configs:
                        GPIO.cleanup(list(self.pin_configs.keys()))
                        print(f"GPIOController: Cleaned up pins: {list(self.pin_configs.keys())}")
                        self.pin_configs.clear()
                        action_taken = True
                    else:
                        print("GPIOController: No pins were configured by this instance to clean up individually. General GPIO.cleanup() if needed.")
                        # Optionally, call general GPIO.cleanup() if you want to be sure, but it cleans up everything.
                        # GPIO.cleanup() # This cleans ALL channels, not just those used by this instance.
                        # print("GPIOController: Called general GPIO.cleanup().")
                elif isinstance(pin, int):
                    self._validate_pin(pin)
                    if pin in self.pin_configs:
                        GPIO.cleanup(pin)
                        del self.pin_configs[pin]
                        print(f"GPIOController: Cleaned up pin {pin}")
                        action_taken = True
                elif isinstance(pin, list):
                    pins_to_cleanup = [p for p in pin if p in self.pin_configs]
                    if pins_to_cleanup:
                        GPIO.cleanup(pins_to_cleanup)
                        for p in pins_to_cleanup: del self.pin_configs[p]
                        print(f"GPIOController: Cleaned up pins: {pins_to_cleanup}")
                        action_taken = True
            else: # Mocked GPIO cleanup
                if pin is None:
                    self.pin_configs.clear()
                    print("MockGPIO (via Controller): Cleared all pin configs.")
                    action_taken = True
                elif isinstance(pin, int) and pin in self.pin_configs:
                    del self.pin_configs[pin]
                    print(f"MockGPIO (via Controller): Cleared config for pin {pin}.")
                    action_taken = True
                elif isinstance(pin, list):
                    for p in pin:
                        if p in self.pin_configs: del self.pin_configs[p]
                    print(f"MockGPIO (via Controller): Cleared config for pins {pin}.")
                    action_taken = True
            
            if not action_taken and pin is not None:
                 print(f"GPIOController: Pin {pin} (or list) was not in the set of pins managed by this controller instance, no specific cleanup action taken.")

        except Exception as e:
            # Catch errors during cleanup (e.g., if GPIO lib has issues)
            # but don't let it stop the __exit__ process if called from there.
            print(f"GPIOController Warning: Error during GPIO cleanup for pin '{pin}': {e}")

    def __enter__(self):
        # Initialization is done in __init__
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup all pins managed by this instance on exit
        print("GPIOController: Exiting context, cleaning up managed GPIO pins.")
        self.cleanup() # Cleans all pins registered with this instance 