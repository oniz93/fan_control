#!/usr/bin/env python3
"""
This script sets up a CherryPy web server to control an Arduino-based fan controller.
It listens for GET requests in the format:
    http://<server_ip>:8080/<name>/<temperature>
where:
  - <name> is an identifier for the source of the temperature reading.
  - <temperature> is a numeric value representing the temperature (e.g., a GPU temperature).

Main functionalities:
1. **Key-Value Storage with Expiration:**
   - Incoming temperature values are stored in a key-value store where each key (identified by <name>)
     is associated with a tuple (temperature, timestamp).
   - Each entry expires after 10 minutes. Expired keys are removed when a new GET request is processed.

2. **Fan Duty Cycle Computation:**
   - After updating the key-value store, the highest temperature value is extracted.
   - The duty cycle is computed based on the following rules:
       - If the maximum temperature is below 35°C, the duty cycle is set to 20%.
       - If it is above 70°C, the duty cycle is set to 100%.
       - Otherwise, a linear interpolation is applied between 20% and 100%.

3. **Arduino Communication:**
   - The computed duty cycle is sent to an Arduino over a serial connection.
   - The Arduino is configured to use the serial port '/dev/ttyACM0' with a baud rate of 115200.

4. **Single Instance Enforcement:**
   - Before starting the server, the script checks if the chosen port (8080) is available.
   - If the port is already in use, it assumes another instance is running and exits gracefully.

Usage:
   - Ensure that the Arduino is connected and the serial port settings are correct.
   - Start the script:
         ./this_script.py
   - To update fan control, send a GET request following the URL pattern:
         http://<server_ip>:8080/<name>/<temperature>
   - Console output provides diagnostic messages for each operation.

This documentation is provided to help developers unfamiliar with the project understand the purpose and structure of the script,
making future modifications and maintenance easier.
"""

import sys
import time
import socket
import cherrypy
import serial
import logging
from logging.handlers import RotatingFileHandler

# Set up the logger
logger = logging.getLogger('fan_control')
logger.setLevel(logging.INFO)

# Configure the RotatingFileHandler
handler = RotatingFileHandler(
    filename='control_fan.log',
    maxBytes=1 * 1024 * 1024,  # 1MB
    backupCount=5  # Keep 5 backup files
)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Redirect stdout and stderr to the logger
class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass

sys.stdout = StreamToLogger(logger, logging.INFO)
sys.stderr = StreamToLogger(logger, logging.ERROR)

# Arduino configuration
arduino_port = '/dev/ttyACM0'
baud_rate = 115200

def compute_duty_cycle(max_temp):
    """Compute the Arduino duty cycle based on the maximum GPU temperature."""
    if max_temp < 35:
        return 20
    elif max_temp > 70:
        return 100
    else:
        return int(20 + (max_temp - 35) * (80 / 35))

def control_fan(duty_cycle):
    """Send the duty cycle to the Arduino over a serial connection."""
    try:
        with serial.Serial(arduino_port, baud_rate, timeout=2) as arduino:
            arduino.write(f"{duty_cycle}\n".encode('utf-8'))
            logger.info(f"Arduino fan duty cycle set to {duty_cycle}%")
    except Exception as e:
        logger.error(f"Error communicating with Arduino: {e}")

class FanController(object):
    # Dictionary to store values: key is name, value is a tuple (temperature, timestamp)
    kv_store = {}
    expire_seconds = 600  # 10 minutes

    @cherrypy.expose
    def default(self, *args, **kwargs):
        # Expecting a URL format: /<name>/<temperature>
        if len(args) != 2:
            raise cherrypy.HTTPError(400, "Invalid URL format. Expected /<name>/<temperature>")
        name, temperature_str = args

        try:
            temperature = float(temperature_str)
        except ValueError:
            raise cherrypy.HTTPError(400, "Temperature must be a number")

        current_time = time.time()

        # Remove expired keys from the kv_store
        expired_keys = [
            key for key, (_, timestamp) in self.kv_store.items()
            if current_time - timestamp > self.expire_seconds
        ]
        for key in expired_keys:
            del self.kv_store[key]

        # Update the store with the new value
        self.kv_store[name] = (temperature, current_time)
        logger.info(f"Updated kv_store: {self.kv_store}")

        # Find the highest temperature currently stored
        if self.kv_store:
            max_temp = max(val for (val, ts) in self.kv_store.values())
        else:
            max_temp = temperature  # fallback; should never happen as we just inserted

        # Compute the new duty cycle and update the fan
        duty_cycle = compute_duty_cycle(max_temp)
        logger.info(f"Computed duty cycle {duty_cycle}% from max temperature {max_temp}")
        control_fan(duty_cycle)

        return f"Received {name} with temperature {temperature}. Duty cycle set to {duty_cycle}%.\n"

def is_port_in_use(port, host="0.0.0.0"):
    """Try binding a socket to check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except socket.error:
            return True

if __name__ == "__main__":
    # Configuration for the CherryPy web server
    port = 8080
    host = "0.0.0.0"

    # Check if the port is already in use; if so, exit to prevent multiple instances.
    if is_port_in_use(port, host):
        logger.info(f"Server already running on port {port}. Exiting.")
        sys.exit(0)

    # CherryPy server configuration
    cherrypy.config.update({
        'server.socket_host': host,
        'server.socket_port': port,
        'engine.autoreload.on': False  # Disable autoreload to avoid spawning new processes
    })

    # Mount our FanController to the root URL
    cherrypy.tree.mount(FanController(), '/')
    logger.info(f"Starting CherryPy server on {host}:{port}")
    cherrypy.engine.start()
    cherrypy.engine.block()