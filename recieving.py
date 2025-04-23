# This file shall be used to receive contents over serial.
import serial

from signal import signal, SIGINT
from sys import exit
ser=serial.Serial(port="/dev/ttyACM0", baudrate=115200)
read_values=""
count=0     #counts the number of logs
def handler(signal_received, frame):
    # Handle any cleanup here
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    
    ser.close()
    exit(0)

def receive(read_values):       
    read_values=ser.readline().decode()
    
def send(read_values):
    read_list=read_values.split("_")
    return read_list



signal(SIGINT, handler)   
while True:
    receive(read_values)
    count+=1
    if read_values:
        print(f"Log {count}")
        print(send(read_values), end="\n")

