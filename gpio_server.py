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
VALID_PINS = [2, 3, 4, 7, 8, 9, 10, 11, 12, 14, 15, 17, 18, 22, 23, 24, 25, 27]

# PWM frequency in Hz (higher = smoother but more CPU usage)
PWM_FREQUENCY = 1000

# Store current pin states and modes
pin_states = {}  # For digital: bool, for PWM: duty cycle (0-100)
pin_modes = {}  # 'output', 'input', or 'pwm'
pwm_instances = {}  # Store PWM objects for cleanup

# L298N Motor Driver Configuration
# Left motor (Motor A) - controls left wheels
MOTOR_LEFT = {
    'enable': 18,  # ENA - PWM speed control
    'in1': 17,     # IN1 - Forward
    'in2': 27      # IN2 - Backward
}

# Right motor (Motor B) - controls right wheels
MOTOR_RIGHT = {
    'enable': 12,  # ENB - PWM speed control
    'in3': 22,     # IN3 - Forward
    'in4': 23      # IN4 - Backward
}

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

# =============================================================================
# L298N Motor Control Endpoints
# =============================================================================

def set_motor(motor_config, speed):
    """
    Control a single motor connected to L298N driver.

    Args:
        motor_config: MOTOR_LEFT or MOTOR_RIGHT configuration dict
        speed: -100 to 100 (negative = backward, positive = forward, 0 = stop)
    """
    # Determine direction pins based on motor
    if motor_config == MOTOR_LEFT:
        in_fwd = motor_config['in1']
        in_bwd = motor_config['in2']
    else:
        in_fwd = motor_config['in3']
        in_bwd = motor_config['in4']

    # Setup direction pins as outputs
    GPIO.setup(in_fwd, GPIO.OUT)
    GPIO.setup(in_bwd, GPIO.OUT)

    # Set direction based on speed sign
    if speed > 0:
        # Forward
        GPIO.output(in_fwd, GPIO.HIGH)
        GPIO.output(in_bwd, GPIO.LOW)
    elif speed < 0:
        # Backward
        GPIO.output(in_fwd, GPIO.LOW)
        GPIO.output(in_bwd, GPIO.HIGH)
    else:
        # Stop (brake)
        GPIO.output(in_fwd, GPIO.LOW)
        GPIO.output(in_bwd, GPIO.LOW)

    # Set speed via PWM (use absolute value)
    abs_speed = min(abs(speed), 100)
    enable_pin = motor_config['enable']
    setup_pin_pwm(enable_pin)
    pwm_instances[enable_pin].ChangeDutyCycle(abs_speed)
    pin_states[enable_pin] = abs_speed

@app.route('/motor/drive', methods=['POST'])
def motor_drive():
    """
    Drive the RC car by setting left and right motor speeds.

    JSON body:
        left: -100 to 100 (left motor speed, negative = backward)
        right: -100 to 100 (right motor speed, negative = backward)

    Examples:
        Forward: {"left": 70, "right": 70}
        Backward: {"left": -70, "right": -70}
        Turn right: {"left": 70, "right": 30}
        Spin left: {"left": -50, "right": 50}
    """
    try:
        data = request.get_json()
        left = data.get('left', 0)
        right = data.get('right', 0)

        # Clamp values to valid range
        left = max(-100, min(100, int(left)))
        right = max(-100, min(100, int(right)))

        # Set both motors
        set_motor(MOTOR_LEFT, left)
        set_motor(MOTOR_RIGHT, right)

        logger.info(f"Motor drive: left={left}, right={right}")

        return jsonify({
            'success': True,
            'left': left,
            'right': right
        })

    except Exception as e:
        logger.error(f"Error driving motors: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/motor/stop', methods=['POST'])
def motor_stop():
    """Emergency stop - immediately stops all motors"""
    try:
        # Stop left motor
        GPIO.setup(MOTOR_LEFT['in1'], GPIO.OUT)
        GPIO.setup(MOTOR_LEFT['in2'], GPIO.OUT)
        GPIO.output(MOTOR_LEFT['in1'], GPIO.LOW)
        GPIO.output(MOTOR_LEFT['in2'], GPIO.LOW)

        # Stop right motor
        GPIO.setup(MOTOR_RIGHT['in3'], GPIO.OUT)
        GPIO.setup(MOTOR_RIGHT['in4'], GPIO.OUT)
        GPIO.output(MOTOR_RIGHT['in3'], GPIO.LOW)
        GPIO.output(MOTOR_RIGHT['in4'], GPIO.LOW)

        # Set PWM to 0 on enable pins
        for enable_pin in [MOTOR_LEFT['enable'], MOTOR_RIGHT['enable']]:
            if enable_pin in pwm_instances:
                pwm_instances[enable_pin].ChangeDutyCycle(0)
                pin_states[enable_pin] = 0

        logger.info("Motors stopped")

        return jsonify({
            'success': True,
            'status': 'stopped'
        })

    except Exception as e:
        logger.error(f"Error stopping motors: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/motor/status', methods=['GET'])
def motor_status():
    """Get current motor status"""
    try:
        return jsonify({
            'success': True,
            'left': {
                'enable_pin': MOTOR_LEFT['enable'],
                'speed': pin_states.get(MOTOR_LEFT['enable'], 0)
            },
            'right': {
                'enable_pin': MOTOR_RIGHT['enable'],
                'speed': pin_states.get(MOTOR_RIGHT['enable'], 0)
            }
        })
    except Exception as e:
        logger.error(f"Error getting motor status: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
