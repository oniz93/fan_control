#!/usr/bin/env python3
import subprocess
import os
import shutil
import sys

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
        print(f"Error retrieving GPU temperatures: {e}")
        return None

def init_libraries():
    """Check if the required tool 'py-nvtool' is available."""
    if shutil.which("py-nvtool") is None:
        print("The py-nvtool package must be installed and available in PATH.")
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
        print(f"GPU{i} Temperature: {temp}°C | Fan set to: {gpu_fan}%")
        # Use py-nvtool to set the GPU fan speed
        subprocess.run(
            ['py-nvtool', '--index', str(i), '--setfan', str(gpu_fan)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=os.environ
        )

def compute_duty_cycle(max_temp):
    """Compute the Arduino duty cycle based on the maximum GPU temperature."""
    if max_temp < 35:
        return 20
    elif max_temp > 70:
        return 100
    else:
        return int(20 + (max_temp - 35) * (80 / 35))

def main():
    if not init_libraries():
        sys.exit(1)

    temperatures = get_gpu_temperature()
    if temperatures:
        max_temp = max(temperatures)
        set_gpu_fans(temperatures)
        duty_cycle = compute_duty_cycle(max_temp)
        print(f"Max GPU Temperature: {max_temp}°C | Arduino Fan Duty Cycle: {duty_cycle}%")
    else:
        print("Unable to read GPU temperatures.")

if __name__ == "__main__":
    main()