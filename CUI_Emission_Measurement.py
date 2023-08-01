#%%
import time
import DK480_control
import LI5640_class

WAIT_TIME = 0.1
WL_start = 2750
WL_end = 5000
span = WL_end - WL_start
step = 5
SampleN = int(span/step)
#%%
inst_DK = DK480_control.Connect()
DK = DK480_control.DK480(inst_DK)
# DK.GratingSelect(3)
#%%
DK.SlitAdjust(3000)
DK.GoTo(WL_start)
#%%
inst_LI = LI5640_class.Connect('GPIB0::2::INSTR')
LIA1 = LI5640_class.Lockin(inst_LI)
LIA1.Initialize()
#%%
import numpy as np
WL = WL_start
WL_list = list()
data_list = list()

for i in range (SampleN):
    DK.GoTo(WL)
    time.sleep(WAIT_TIME)
    data = inst_LI.query('DOUT?')
    data = np.array(data.split(","), dtype='float64')

    WL_list.append(WL)
    data_list.append(data)
    WL = WL + step
    pass
# %%
import matplotlib.pyplot as plt
data_list = np.array(data_list)
WL_list = np.array(WL_list)
plt.plot(WL_list, data_list)
# %%
import os
import datetime

folder = r'C:\Users\okazaki\Desktop\Datas\Test'
dataname = 'Nd3600ppm_current_1450mA_thick'
directory = folder + str(datetime.date.today())
dammy = np.zeros(len(WL_list))

savedata = np.array([dammy,WL_list,data_list.flatten()])
saves = savedata.transpose()

def duplicate_rename(filename):
    new_name = filename
    global times
    if os.path.exists(filename):
        name, ext = os.path.splitext(filename)
        while True:
            new_name = "{}{}_again{}".format(directory, '_Spectrum', ext)
            if not os.path.exists(new_name):
                return new_name
    else:
        return new_name

filename0 = "{}{}{}".format(directory, dataname, '.csv')
filename0 = duplicate_rename(filename0)

try:
    np.savetxt(filename0, saves, fmt="%.10f",delimiter=",")# 保存する文字列。
    print('ファイルは正常に保存されました。')
except:
    print('ERROR:ファイルの保存に失敗しました。')
# %%
