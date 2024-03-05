
#%%
import pyvisa
import time
import numpy as np
import time
import serial
from serial.tools import list_ports
import threading
import DK480_control, SDS2352X_control
import matplotlib.pyplot as plt

REFRESH_SERIAL_READ = 1e-4
WAIT_TIME = 1e-1

        
if __name__ == '__main__':
    # CM110_control = DK480_control.DK480Control(port="COM6", baudrate=9600)
    # if CM110_control.connect():
    #     print('Connected to CM110')
    
    import SDS2352X_control # visaの取
    inst_SDS = SDS2352X_control.connect('USB0::0xF4EC::0x1010::SDS2EBAD3R0417::INSTR')
    SDS = SDS2352X_control.Oscilloscope(inst_SDS)
    time.sleep(1)
    SDS.set_vdiv('c1', 500)
    SDS.set_ofset('c1', 0)
    SDS.set_vdiv('c2', 2000)
    SDS.set_ofset('c2', 0)
    SDS.set_tdiv(0.002)
    SDS.set_datasize(7)
    vdiv_float, ofst_float, tdiv_float, sara_float = SDS.query_param()
    vdiv = inst_SDS.write("mtvd 2000mV")
    
    data = SDS.get_c1(vdiv_float, ofst_float)
    plt.figure(1, figsize=(12,6))
    plt.plot(data, '.')
    
   
    data = SDS.get_math()
    plt.figure(2, figsize=(12,6))
    plt.plot(data, '.')
# %%
