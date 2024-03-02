
#%%
import pyvisa
import time
import numpy as np
import time
import serial
from serial.tools import list_ports
import threading
import DK480_control, LI5640_control

REFRESH_SERIAL_READ = 1e-4
WAIT_TIME = 1e-1

        
if __name__ == '__main__':
    # CM110_control = DK480_control.DK480Control(port="COM6", baudrate=9600)
    # if CM110_control.connect():
    #     print('Connected to CM110')
    import LI5640_control # visaの取
    inst_LI = LI5640_control.connect('USB0::0xF4EC::0x1010::SDS2EDDD7R1135::INSTR')
    print('Data Acquision system is ready')
# %%
