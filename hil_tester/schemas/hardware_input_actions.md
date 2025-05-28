{
  "test_name": "Simple GPIO 12 Pulse Test",
  "pin_setup": {
    "mode": "BCM"
  },
  "emulation_sequence": [
    {
      "action_id": "setup_gpio12_out",
      "type": "set_gpio_direction",
      "pin": 12,
      "direction": "output",
      "initial_state": "low",
      "description": "Setup GPIO 12 as output, initially low."
    },
    {
      "action_id": "delay_before_pulse",
      "type": "delay_ms",
      "duration": 100
    },
    {
      "action_id": "pulse_gpio12_high",
      "type": "pulse_gpio_output",
      "pin": 12,
      "duration_ms": 500,
      "pulse_state": "high",
      "initial_state": "low",
      "description": "Pulse GPIO 12 HIGH for 500ms to signal STM32."
    },
    {
      "action_id": "delay_after_pulse",
      "type": "delay_ms",
      "duration": 100
    }
  ]
} 