#%%
import pyvisa
import pylab as pl
import numpy as np

def main():
    _rm = pyvisa.ResourceManager()
    sds = _rm.open_resource("USB0::0xF4EC::0x1010::SDS2EBAD3R0417::INSTR")
    sds.write("chdr off")
    vdiv = sds.write("c1:vdiv 10mV")
    print(f'{sds.query("c1:vdiv?")}')

    
    vdiv = sds.write("mtvd 1mV") ##
    print(f'{sds.query("mtvd?")}') ##
    
    ofst = sds.write("c1:ofst 0mV")
    print(f'{sds.query("c1:ofst?")}')
    tdiv = sds.write("tdiv 0.0001s")
    print(f'{sds.query("tdiv?")}')
    msiz = sds.write("msiz 7K")
    print(f'{sds.query("msiz?")}')
    
    vdiv = sds.query("mtvd?")
    ofst = sds.query("c1:ofst?")
    tdiv = sds.query("tdiv?")
    
    vdiv_float = np.float32(vdiv)
    ofst_float = np.float32(ofst)
    tdiv_float = np.float32(tdiv)

    sara = sds.query("sara?")
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
    print(f'{sds.query("sara?")}')
    
    sds.timeout = 30000 #default value is 2000(2s)
    sds.chunk_size = 20*1024*1024 #default value is 20*1024(20k bytes)
    sds.write("math:wf? dat2")
    
    recv = np.array(list(sds.read_raw())[15:-2])  # This slices off the last two elements directly
    volt_value = np.where(recv > 127, recv - 255, recv)
    volt_value = np.array(volt_value)
    volt_value = volt_value / 25 * vdiv_float
    time_value = []
    
    # recv = list(sds.read_raw())[15:]
    # recv.pop()
    # recv.pop()
    # volt_value = []
    # for data in recv:
    #     if data > 127:
    #        data = data - 255
    #     else:
    #         pass
    #     volt_value.append(data)
    # volt_value1 = np.array(volt_value)
    # volt_value = volt_value1 / 25 * vdiv_float # - ofst_float
    
    indices = np.arange(len(volt_value))
    time_value = -(tdiv_float * 14 / 2) + indices * (1 / sara_float)
            
    pl.figure(figsize=(7,5))
    pl.plot(time_value,volt_value,markersize=12,color='r',label=u"Y-T")
    pl.legend()
    pl.grid()
    pl.show()
    return time_value, volt_value

def get_char_bit(char,n):
    return (char >> n) & 1

if __name__=='__main__':
    time_value, volt_value = main()
# %%

# %%
