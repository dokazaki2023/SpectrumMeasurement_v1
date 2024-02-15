# -*- coding: utf-8 -*-
"""
# Created on Tue Jul 20 13:41:52 2021
# @author: Ko Arai (Ashihara lab), modified by Daiki Okazaki
"""
import pyvisa
import time
import numpy as np

def connect(resource_name):
    #Connect to the specified resource and return the instrument object
    try:
        rm = pyvisa.ResourceManager('visa64.dll')
        print('接続可能なインターフェースは:')
        print(rm.list_resources())
    except Exception as e:
        print('Visa Error: Check NI-VISA, visa64.dll etc.')
        raise e

    try:
        inst = rm.open_resource(resource_name)
        inst.write("*CLS")
        inst.write("*RST")
        print(f'{inst.query("*IDN?")}に接続しました')
        return inst
    except Exception as e:
        print('Connection error: Check USB connection, NI-488.2 etc. or restart the machine')
        raise e

class Lockin:
    def __init__(self, inst):
        self.inst = inst

    def initialize(self):
        #Initialize the lock-in amplifier with predefined settings
        settings = {
            "ISRC": "0",  # Input Source A
            "ICPL": "0",  # Input Coupling AC
            "VSEN": "20", # Voltage Sensitivity 10 mV
            "DRSV": "2",  # Dynamic Reserve Low
            "TCON": "8",  # Time Constant 100 ms
            "IFREQ": "1", # 60Hz
            "IGND": "0",  # Ground Float
        }
        command = ";".join([f"{k} {v}" for k, v in settings.items()]) + ";*WAI"
        self.inst.write(command)
        self.inst.write("DDEF 1,1;OTYP 1;*WAI")  # Data -> R, Output -> Data 1
        print('Initialize succeeded')

    def prepare_R(self):
        #Prepare the device for R measurement
        self.inst.write("STOP")  # Stop in case it's recording
        self.inst.write("DNUM 0")  # Data memory number
        self.inst.write("DSIZ 0")  # Recording sample number 2K
        self.inst.write("DSMP 11") # Sampling Ratio 100 ms
        self.inst.write("STRT")    # Ready state

    def trigger(self):
        #Trigger data acquisition
        self.inst.write("*TRG")

    def get_R(self):
        #Retrieve and return R data as a numpy array
        raw_data = self.inst.query('DOUT?')
        return np.array(raw_data.split(","), dtype='float64')

    def set_parameter(self, command, value):
        #Set a specific parameter of the device
        self.inst.write(f"{command} {value}")

    def reference_source(self):
        self.set_parameter("RSRC", "0")

    def dynamic_reserve(self):
        self.set_parameter("DRSV", "0")

    def sensitivity(self):
        self.set_parameter("VSEN", "0")

    def time_constant(self):
        self.set_parameter("TCON", "0")
