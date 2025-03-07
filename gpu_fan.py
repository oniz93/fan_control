#!/usr/bin/env python3
"""
This script continuously monitors GPU temperatures and controls the GPU fan speeds based on the retrieved values.
It is designed to run indefinitely with a 500ms delay between temperature checks and includes the following functionality:

1. **GPU Temperature Monitoring:**
   - Retrieves GPU temperatures using `nvidia-smi`.
   - Parses the output to obtain temperature values for each GPU.

2. **Fan Speed Control:**
   - For each GPU, calculates the appropriate fan speed using the following logic:
       - If temperature < 30°C: set fan speed to 40%.
       - If temperature > 50°C: set fan speed to 100%.
       - Otherwise, linearly interpolate the fan speed between 40% and 100%.
   - Applies the fan speed settings using the `py-nvtool` utility.

3. **External Control Notification:**
   - Loads configuration from a `.env` file. The required parameters are:
       - `MACHINE_NAME`: Identifier for the machine.
       - `CONTROL_IP`: IP address of the control server.
       - `CONTROL_PORT`: Port number of the control server.
   - After setting the GPU fans, it sends a GET request to:
     `http://{CONTROL_IP}:{CONTROL_PORT}/{MACHINE_NAME}/{max_temp}`
   - The request is retried up to 3 times if it fails before moving to the next cycle.

4. **Single Instance Enforcement:**
   - Ensures only one instance of the script is running at a time by binding to a specific local TCP port (default: 9999).
   - If another instance is detected (port already in use), the script exits gracefully.

5. **Usage & Dependencies:**
   - **Usage:** Place a valid `.env` file in the same directory with the required configuration variables and execute the script:
         ./your_script_name.py
   - **Dependencies:** Python 3, `nvidia-smi`, `py-nvtool`, `python-dotenv`, and `requests`.

This comprehensive docblock should provide a clear understanding of the script's purpose and how to modify its behavior if needed.
"""

import subprocess
import os
import shutil
import sys
import time
import socket
import requests
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Set up the logger
logger = logging.getLogger('gpu_fan')
logger.setLevel(logging.INFO)

# Configure the RotatingFileHandler
handler = RotatingFileHandler(
    filename='gpu_fan.log',
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

def get_gpu_temperature():
    """Retrieve GPU temperatures using nvidia-smi."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=temperature.gpu', '--format=csv,noheader,nounits'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        temperatures = result.stdout.splitlines()
        gpu_temps = [int(temp) for temp in temperatures if temp.strip()]
        return gpu_temps if gpu_temps else None
    except Exception as e:
        logger.error(f"Error retrieving GPU temperatures: {e}")
        return None

def init_libraries():
    """Check if the required tool 'py-nvtool' is available."""
    if shutil.which("py-nvtool") is None:
        logger.error("The py-nvtool package must be installed and available in PATH.")
        return False
    return True

def set_gpu_fans(temperatures):
    """
    For each GPU, compute and set the fan speed:
      - If temp < 30°C: set fan to 40%
      - If temp > 50°C: set fan to 100%
      - Otherwise, interpolate linearly between 40% and 100%
    """
    for i, temp in enumerate(temperatures):
        if temp < 30:
            gpu_fan = 40
        elif temp > 50:
            gpu_fan = 100
        else:
            gpu_fan = int(40 + (temp - 30) * (60 / 20))
        gpu_fan = int(max(40, min(100, gpu_fan)))
        logger.info(f"GPU{i} Temperature: {temp}°C | Fan set to: {gpu_fan}%")
        # Use py-nvtool to set the GPU fan speed
        subprocess.run(
            ['py-nvtool', '--index', str(i), '--setfan', str(gpu_fan)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ
        )

def check_single_instance(port=9999, host="127.0.0.1"):
    """Bind to a port to ensure only one instance is running."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((host, port))
    except socket.error:
        logger.info("Another instance is already running. Exiting.")
        sys.exit(0)
    return s  # Hold this socket open for the lifetime of the script

def send_get_request(url, retries=3):
    """Send a GET request to the specified URL, retrying if it fails."""
    for attempt in range(1, retries+1):
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                logger.info(f"GET request succeeded: {url}")
                return True
            else:
                logger.error(f"GET request failed with status {response.status_code}: {url}")
        except Exception as e:
            logger.error(f"GET request error on attempt {attempt}: {e}")
        time.sleep(0.1)
    logger.error(f"Failed to send GET request after {retries} attempts: {url}")
    return False

def main():
    # Load configuration from .env file
    load_dotenv()
    MACHINE_NAME = os.getenv("MACHINE_NAME", "default_machine")
    CONTROL_IP = os.getenv("CONTROL_IP", "127.0.0.1")
    CONTROL_PORT = os.getenv("CONTROL_PORT", "8080")

    # Check if the required library is available
    if not init_libraries():
        sys.exit(1)

    # Ensure only one instance of the script is running
    instance_socket = check_single_instance()

    while True:
        try:
            temperatures = get_gpu_temperature()
            if temperatures:
                max_temp = max(temperatures)
                set_gpu_fans(temperatures)
                logger.info(f"Max GPU Temperature: {max_temp}°C")
                # Build the URL for the control script
                url = f"http://{CONTROL_IP}:{CONTROL_PORT}/{MACHINE_NAME}/{max_temp}"
                send_get_request(url, retries=3)
            else:
                logger.error("Unable to read GPU temperatures.")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        time.sleep(6)

if __name__ == "__main__":
    main()