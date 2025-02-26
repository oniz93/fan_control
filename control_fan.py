#!/usr/bin/env python3
import sys
import serial

# Arduino configuration
arduino_port = '/dev/ttyACM0'
baud_rate = 115200

def control_fan(duty_cycle):
    try:
        # Open the serial connection and send the duty cycle
        with serial.Serial(arduino_port, baud_rate, timeout=2) as arduino:
            arduino.write(f"{duty_cycle}\n".encode('utf-8'))
            print(f"Arduino fan duty cycle set to {duty_cycle}%")
    except Exception as e:
        print(f"Error communicating with Arduino: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python control_fan.py <duty_cycle>")
        sys.exit(1)
    try:
        duty_cycle = int(sys.argv[1])
    except ValueError:
        print("The duty cycle must be an integer.")
        sys.exit(1)
    control_fan(duty_cycle)