#!/usr/bin/env python3
"""
Raspberry Pi GPIO Control Server
Run this script on your Raspberry Pi Zero W to enable remote GPIO control
Supports both digital on/off and PWM (pulse width modulation) for variable output
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import RPi.GPIO as GPIO
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Valid GPIO pins for Raspberry Pi Zero W
VALID_PINS = [2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 17, 18, 22, 23, 24, 25, 27]

# PWM frequency in Hz (higher = smoother but more CPU usage)
PWM_FREQUENCY = 1000

# Store current pin states and modes
pin_states = {}  # For digital: bool, for PWM: duty cycle (0-100)
pin_modes = {}  # 'output', 'input', or 'pwm'
pwm_instances = {}  # Store PWM objects for cleanup

def cleanup_pwm(pin):
    """Stop and cleanup PWM on a pin if it exists"""
    if pin in pwm_instances:
        pwm_instances[pin].stop()
        del pwm_instances[pin]
        logger.info(f"Stopped PWM on GPIO {pin}")

def setup_pin_output(pin):
    """Setup a pin as output if not already configured"""
    if pin in pin_modes and pin_modes[pin] == 'pwm':
        cleanup_pwm(pin)
    if pin not in pin_modes or pin_modes[pin] != 'output':
        GPIO.setup(pin, GPIO.OUT)
        pin_modes[pin] = 'output'
        pin_states[pin] = False
        GPIO.output(pin, GPIO.LOW)
        logger.info(f"Configured GPIO {pin} as OUTPUT")

def setup_pin_pwm(pin):
    """Setup a pin for PWM output"""
    if pin in pin_modes and pin_modes[pin] == 'pwm':
        return  # Already configured as PWM

    # Cleanup any existing PWM
    cleanup_pwm(pin)

    # Setup pin as output first
    GPIO.setup(pin, GPIO.OUT)

    # Create PWM instance
    pwm = GPIO.PWM(pin, PWM_FREQUENCY)
    pwm.start(0)  # Start with 0% duty cycle
    pwm_instances[pin] = pwm
    pin_modes[pin] = 'pwm'
    pin_states[pin] = 0
    logger.info(f"Configured GPIO {pin} as PWM output")

def setup_pin_input(pin):
    """Setup a pin as input if not already configured"""
    if pin in pin_modes and pin_modes[pin] == 'pwm':
        cleanup_pwm(pin)
    if pin not in pin_modes or pin_modes[pin] != 'input':
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        pin_modes[pin] = 'input'
        logger.info(f"Configured GPIO {pin} as INPUT")

@app.route('/gpio/set', methods=['POST'])
def set_gpio():
    """Set GPIO pin state"""
    try:
        data = request.get_json()
        pin = data.get('gpio')
        state = data.get('state')

        if pin is None or state is None:
            return jsonify({'error': 'Missing gpio or state parameter'}), 400

        if pin not in VALID_PINS:
            return jsonify({'error': f'Invalid GPIO pin: {pin}'}), 400

        # Setup pin as output
        setup_pin_output(pin)

        # Set the pin state
        GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
        pin_states[pin] = state

        logger.info(f"Set GPIO {pin} to {'HIGH' if state else 'LOW'}")

        return jsonify({
            'success': True,
            'gpio': pin,
            'state': state
        })

    except Exception as e:
        logger.error(f"Error setting GPIO: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/gpio/pwm', methods=['POST'])
def set_pwm():
    """Set GPIO pin PWM duty cycle (0-100)"""
    try:
        data = request.get_json()
        pin = data.get('gpio')
        duty_cycle = data.get('dutyCycle')

        if pin is None or duty_cycle is None:
            return jsonify({'error': 'Missing gpio or dutyCycle parameter'}), 400

        if pin not in VALID_PINS:
            return jsonify({'error': f'Invalid GPIO pin: {pin}'}), 400

        # Validate duty cycle range
        duty_cycle = max(0, min(100, float(duty_cycle)))

        # Setup pin for PWM if not already
        setup_pin_pwm(pin)

        # Set the duty cycle
        pwm_instances[pin].ChangeDutyCycle(duty_cycle)
        pin_states[pin] = duty_cycle

        logger.info(f"Set GPIO {pin} PWM to {duty_cycle}%")

        return jsonify({
            'success': True,
            'gpio': pin,
            'dutyCycle': duty_cycle,
            'mode': 'pwm'
        })

    except Exception as e:
        logger.error(f"Error setting PWM: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/gpio/status', methods=['GET'])
def get_status():
    """Get status of all GPIO pins"""
    try:
        pins = {}
        pwm_pins = {}

        for pin in VALID_PINS:
            # If pin is configured, read its state
            if pin in pin_modes:
                if pin_modes[pin] == 'pwm':
                    # For PWM pins, return duty cycle (0-100)
                    pwm_pins[pin] = pin_states.get(pin, 0)
                    pins[pin] = pin_states.get(pin, 0) > 0  # Also set digital state for compatibility
                elif pin_modes[pin] == 'output':
                    pins[pin] = pin_states.get(pin, False)
                elif pin_modes[pin] == 'input':
                    pins[pin] = GPIO.input(pin) == GPIO.HIGH
            else:
                # Default to False for unconfigured pins
                pins[pin] = False

        return jsonify({
            'success': True,
            'pins': pins,
            'pwm': pwm_pins,
            'modes': pin_modes
        })

    except Exception as e:
        logger.error(f"Error getting GPIO status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/gpio/mode', methods=['POST'])
def set_mode():
    """Set GPIO pin mode (input/output)"""
    try:
        data = request.get_json()
        pin = data.get('gpio')
        mode = data.get('mode')

        if pin is None or mode is None:
            return jsonify({'error': 'Missing gpio or mode parameter'}), 400

        if pin not in VALID_PINS:
            return jsonify({'error': f'Invalid GPIO pin: {pin}'}), 400

        if mode not in ['input', 'output']:
            return jsonify({'error': 'Mode must be "input" or "output"'}), 400

        if mode == 'output':
            setup_pin_output(pin)
        else:
            setup_pin_input(pin)

        return jsonify({
            'success': True,
            'gpio': pin,
            'mode': mode
        })

    except Exception as e:
        logger.error(f"Error setting GPIO mode: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'configured_pins': len(pin_modes),
        'pins': list(pin_modes.keys())
    })

def cleanup():
    """Cleanup GPIO on shutdown"""
    logger.info("Cleaning up GPIO...")
    # Stop all PWM instances first
    for pin in list(pwm_instances.keys()):
        cleanup_pwm(pin)
    GPIO.cleanup()

if __name__ == '__main__':
    try:
        logger.info("Starting Raspberry Pi GPIO Server...")
        logger.info(f"Valid GPIO pins: {VALID_PINS}")
        app.run(host='0.0.0.0', port=3001, debug=True)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        cleanup()
