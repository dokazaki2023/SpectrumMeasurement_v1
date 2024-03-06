"""
# Created on Tue Mar 02 13:41:52 2024
# @author: Daiki Okazaki
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
        # inst.write("*CLS")
        # inst.write("*RST")
        # time.sleep(3)
        time.sleep(0.1)
        inst.write("chdr off")
        inst.timeout = 2000 #default value is 2000(2s)
        inst.chunk_size = 20*1024 #default value is 20*1024(20k bytes)
        print(f'{inst.query("*IDN?")}に接続しました')
        return inst
    except Exception as e:
        print('Connection error: Check USB connection, NI-488.2 etc. or restart the machine')
        raise e

class Oscilloscope:
    def __init__(self, inst):
        self.inst = inst

    def initialize(self):
        print('Initialize succeeded')
        
    def set_parameter(self, command, value):
        self.inst.write(f"{command} {value}")
        # print(f"{command} {value}")

    def set_vdiv(self, channel, volt_mV):
        command = f'{channel}:vdiv'
        value = f'{volt_mV}mV'
        self.set_parameter(command, value)
        
    def set_tdiv(self, time_sec):
        command = 'tdiv'
        value = f'{time_sec}s'
        self.set_parameter(command, value)
    
    def set_ofset(self, channel, volt_mV):
        command = f'{channel}:ofst'
        value = f'{volt_mV}mV'
        self.set_parameter(command, value)

    def set_datasize(self, num_data_K):
        command = 'msiz'
        value = f'{num_data_K}K'
        self.set_parameter(command, value)
    
    def query_param(self):
        vdiv = self.inst.query("c1:vdiv?")
        ofst = self.inst.query("c1:ofst?")
        tdiv = self.inst.query("tdiv?")
        vdiv_float = np.float32(vdiv)
        ofst_float = np.float32(ofst)
        tdiv_float = np.float32(tdiv)
        
        sara = self.inst.query("sara?")
        sara_unit = {'G': 1E9, 'M': 1E6, 'k': 1E3}
        sara_value, unit_found = next(((float(sara.split(unit)[0]) * factor, unit) for unit, factor in sara_unit.items() if unit in sara), (sara, None))
        if unit_found:
            sara = sara_value
        else:
            try:
                sara = float(sara)
            except ValueError:
                pass
        sara_float = np.float32(sara)
        return vdiv_float, ofst_float, tdiv_float, sara_float

    def query_param_math(self):
        self.inst.write("def eqn,'c1*c2'")
        vdiv = self.inst.query("mtvd?") ##
        vdiv_float = np.float32(vdiv)
        ofst_float = vdiv_float*5
        return vdiv_float, ofst_float

    def get_c1(self, vdiv_float, ofst_float):
        self.inst.write("c1:wf? dat2")
        recv = np.array(list(self.inst.read_raw())[15:-2])  # This slices off the last two elements directly
        volt_value = np.where(recv > 127, recv - 255, recv)
        volt_value = np.array(volt_value)
        volt_value = volt_value / 25 * vdiv_float - ofst_float
        return volt_value
    
    def get_math(self ,vdiv_float, ofst_float):
        self.inst.write("math:wf? dat2")
        recv = np.array(list(self.inst.read_raw())[15:-2])  # This slices off the last two elements directly
        volt_value = np.where(recv > 127, recv - 0, recv)
        volt_value = np.array(volt_value)
        volt_value = volt_value * vdiv_float / 25 - ofst_float
        return volt_value
    
