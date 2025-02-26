# fan_control

## Setup host machine

Install required system packages (if not already installed):

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

Create a project directory (for example, fan_control) and move into it OR __you can clone this repository__:
```bash
mkdir ~/fan_control
cd ~/fan_control
```

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages inside the virtual environment:
```bash
pip install pyserial
```

Create `control_fan.py` file and `chmod +x control_fan.py`

Add entry to crontab
```bash
crontab -e
```

```
*/5 * * * * /home/youruser/fan_control/venv/bin/python /home/youruser/fan_control/control_fan.py 80 >> /home/youruser/fan_control/control_fan.log 2>&1
```


## Setup GPU machine

Install required system packages (if not already installed):

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
wget https://github.com/Akisoft41/py-nvtool/releases/download/v0.2.0/py-nvtool.py
chmod +x py-nvtool.py
sudo cp py-nvtool.py /usr/sbin/py-nvtool
```

Create a project directory (for example, fan_control) and move into it OR  __you can clone this repository__:
```bash
mkdir ~/fan_control
cd ~/fan_control
```

Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Create `gpu_fan.py` file and `chmod +x gpu_fan.py`

Add entry to crontab
```bash
sudo crontab -e
```

```
*/5 * * * * /home/youruser/fan_control/venv/bin/python /home/youruser/fan_control/gpu_fan.py >> /home/youruser/fan_control/gpu_fan.log 2>&1
```
