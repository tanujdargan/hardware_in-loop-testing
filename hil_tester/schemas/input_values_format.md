# Hardware Input Actions JSON Format

This JSON file defines sequences of hardware actions to be performed by the Raspberry Pi to emulate inputs for the STM32 device under test. This typically involves controlling GPIO pins.

## Root Object

-   `test_name` (string, optional): A descriptive name for the test.
-   `pin_setup` (object, optional): Defines initial setup for GPIO pins.
    -   `mode` (string, optional): GPIO numbering mode (e.g., "BCM" or "BOARD"). Defaults to "BCM".
-   `emulation_sequence` (array, required): An array of action objects.

## Action Object

Each object in `emulation_sequence` defines a hardware action.

-   `action_id` (string, required): Unique ID for the action.
-   `type` (string, required): Type of hardware action. Examples:
    -   `set_gpio_direction`: Sets a GPIO pin as an OUTPUT or INPUT.
    -   `set_gpio_output`: Sets an output GPIO pin to HIGH or LOW.
    -   `read_gpio_input`: Reads the state of an input GPIO pin (for RPi to sense, if needed for emulation logic).
    -   `pulse_gpio_output`: Creates a pulse on an output GPIO pin.
    -   `delay_ms`: Pauses execution.
    -   `spi_transaction` (conceptual): For SPI communication.
    -   `i2c_write` (conceptual): For I2C communication.
-   `description` (string, optional): Human-readable description.

### Type-Specific Fields:

#### For `set_gpio_direction`:
-   `pin` (integer, required): GPIO pin number (BCM or BOARD based on `pin_setup.mode`).
-   `direction` (string, required): "output" or "input".
-   `initial_state` (string, optional): For "output", can be "high" or "low".
-   `pull_up_down` (string, optional): For "input", can be "pull_up", "pull_down", or "none".

#### For `set_gpio_output`:
-   `pin` (integer, required): GPIO pin number.
-   `value` (string, required): "high" or "low".

#### For `read_gpio_input`:
-   `pin` (integer, required): GPIO pin number.
-   `expected_value_for_log` (string, optional): "high" or "low". The read value will be logged. (Note: This is for RPi logging, not for comparing STM32 output).

#### For `pulse_gpio_output`:
-   `pin` (integer, required): GPIO pin number.
-   `duration_ms` (integer, required): Duration of the active part of the pulse.
-   `pulse_state` (string, optional): "high" or "low" (the state during the pulse). Defaults to "high".
-   `initial_state` (string, optional): The state before and after the pulse. If `pulse_state` is "high", `initial_state` defaults to "low", and vice-versa.

#### For `delay_ms`:
-   `duration` (integer, required): Delay in milliseconds.

#### For `spi_transaction` (Conceptual - requires SPI library):
-   `bus` (integer, required): SPI bus number.
-   `device` (integer, required): SPI device/chip-select number.
-   `data_out_hex` (array of strings, optional): Bytes to send (hex format).
-   `bytes_to_read` (integer, optional): Number of bytes to read back.

## Example Hardware Input JSON:

```json
{
  "test_name": "GPIO Interaction Test",
  "pin_setup": {
    "mode": "BCM"
  },
  "emulation_sequence": [
    {
      "action_id": "setup_led_pin",
      "type": "set_gpio_direction",
      "pin": 17,
      "direction": "output",
      "initial_state": "low"
    },
    {
      "action_id": "setup_button_pin",
      "type": "set_gpio_direction",
      "pin": 18,
      "direction": "input",
      "pull_up_down": "pull_up"
    },
    {
      "action_id": "delay_init",
      "type": "delay_ms",
      "duration": 100
    },
    {
      "action_id": "press_button_signal",
      "type": "set_gpio_output",
      "pin": 17, 
      "value": "high",
      "description": "Simulate pressing a button by driving pin 17 HIGH (assuming STM32 senses this via pin 18 being pulled low externally by this)"
    },
    {
      "action_id": "hold_button",
      "type": "delay_ms",
      "duration": 500
    },
    {
      "action_id": "release_button_signal",
      "type": "set_gpio_output",
      "pin": 17,
      "value": "low"
    }
  ]
} 