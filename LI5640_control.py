# -*- coding: utf-8 -*-
"""
Created on Tue Jul 20 13:41:52 2021

@author: Ko Arai (Ashihara lab), 
            modified by Daiki Okazaki
"""

import pyvisa # visaの取得
import time
import numpy as np

def Connect(ResourceName):
    try:
        rm = pyvisa.ResourceManager('visa64.dll') # visaのdllの取得
        print('接続可能なインターフェースは')
        print(rm.list_resources()) # 接続機器のリストアップ
    except Exception as e:
        print('Visa Error')
        print('Check NI-VISA, visa64.dll etc.')
        print(e)
        
    try:
        inst = rm.open_resource(ResourceName) # 接続機器の選択
        inst.write("*CLS")
        inst.write("*RST")
        print(str(inst.query("*IDN?")) + 'に接続しました')  # 通信テスト　機器の名前を聞く
    except Exception as e:
        print('Connection error')
        print('Check USB connection, NI-488.2 etc. or restart the machine')
        print(e)
    return inst
    
class Lockin:
    def __init__(self, inst):
        self.inst = inst
    
    def Initialize(self):
        self.inst.timeout = 25000
        # ISRC:Input Source A, ICPL:Input Coupling AC, VSEN:Voltage Sensitivity 10 mV, 
        # DRSV:Dynamic Reserve Low, TCON:Time Constant 100 ms, IFREQ:50Hz/60Hz -> 60Hz, IGND:Ground Float
        self.inst.write("ISRC 0;ICPL 0;VSEN 20;DRSV 2;TCON 8;IFREQ 1;IGND 0;*WAI") #AC 結合に
        self.inst.write("DDEF 1,1;OTYP 1;*WAI") # Data -> R, Output -> Data 1
        print('Initialize succeeded')

    def Prepare_R(self):
        self.inst.write("STOP") #記録中などの場合、中断
        self.inst.write("DNUM 0") # Data memoru number
        self.inst.write("DSIZ 0") # 記録サンプル数 2K        
        self.inst.write("DSMP 11") # Sampling Ratio 100 ms
        self.inst.write("STRT") # ready 状態に移行
        
    def Trigger(self):
        self.inst.write("*TRG") #データ取得開始
        
    def Get_R(self):
        raw_data = self.inst.query('DOUT?') # データをもらう
        data = np.array(raw_data.split(","), dtype='float64') #numpy にしとく
        return data
    
    def ReferenceSource(self):
        self.inst.write("RSRC 0")
        return
    
    def DynamicReserve(self):
        self.inst.write("DRSV 0")
        return
    
    def Sensitivity(self):
        self.inst.write("VSEN 0")
        return
    
    def TimeConstant(self):
        self.inst.write("TCON 0")
        return
    
