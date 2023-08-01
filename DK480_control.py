# -*- coding: utf-8 -*-
"""
Created on Sat May 27 08:28:22 2023

@author: Daiki Okazaki @ Laser 
"""

#%%
import time
import serial
import struct
from serial.tools import list_ports
import numpy as np

from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot, QThreadPool
import uuid

REFLESH_SERIAL_READ = 1e-4
WAIT_TIME = 1e-1

def Connect(baudrate=9600):
    global ser
    ser = serial.Serial()
    ser.baudrate = baudrate
    ser.rtscts = True
    ser.dsrdtr = False
    ser.timeout = 2*REFLESH_SERIAL_READ
    ports = list_ports.comports()    # ポートデータを取得
    devices = [info.device for info in ports]
    print("Number of controller: {0}".format(devices))

    if len(devices) == 0: # シリアル通信できるデバイスが見つからなかった場合
        print("エラー: ポートが見つかりませんでした")
        return None
    else:
        try:
            ser = serial.Serial("COM4",  baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=REFLESH_SERIAL_READ)
        except Exception as e:
            print("エラー：ポートが開けませんでした。")
            print(e)
        else:
            ser.close()
            return ser

def binary_to_string_UTF(result):
    # print(result)
    try:
        result_string = ord(result.strip().decode('utf-8'))
    except:
        result_string = 0
    return result_string

def binary_to_string_ShiftJis(result):
    # print(result)
    try:
        result_string = ord(result.strip().decode('shift-jis'))
    except:
        result_string = 0
    return result_string

def binary_to_string(result):
    # print(result)
    try:
        result_string = result.decode('shift-jis', 'replace')
    except:
        result_string = 0
    return result_string

class DK480:
    def __init__(self, ser):    
        self.ser = ser
        self.threadpool = QThreadPool()
        
    def WavelengthConvert(self, Wavelength):
        Wavelength = int(Wavelength*100)
        Wavelength16 = hex(Wavelength)
        if Wavelength16.startswith('0x'):
            data = Wavelength16[2:]
            Low = data[-2:]
            Mid = data[-4:-2]
            if len(data) == 1:
                High = '00'
                Mid = '00'
                Low = '0' + data[-1]
            elif len(data) == 2:
                High = '00'
                Mid = '00'
            elif len(data) == 3:
                High = '00'
                Mid = '0' + data[-3]
            elif len(data) == 4:
                High = '00'
            elif len(data) == 5:
                High = '0' + data[0]
            else:
                High = data[0:1]
        High = int(High, 16)
        Mid = int(Mid, 16)
        Low = int(Low, 16)
        return  High, Mid, Low
    
    def SpeedConvert(self, Wavelength_Speed):
        Wavelength_Speed = int(Wavelength_Speed)
        Wavelength_Speed16 = hex(Wavelength_Speed)
        if Wavelength_Speed16.startswith('0x'):
            data = Wavelength_Speed16[2:]
            Low = data[-2:]
            if len(data) == 2:
                High = '00'
            elif len(data) == 3:
                High = '0' + data[0]
            else:
                High = data[-4:-2]
        High = int(High, 16)
        Low = int(Low, 16)
        return  High, Low

    def GratingSelect(self, GratingID):
        # To DK240/480: <26> GRTSEL
        self.ser.open()
        Command = chr(26)
        self.ser.write(Command.encode('utf-8'))
        self.IsSend(Command) 

        # To DK240/480: One Byte Grating ID
        Command = chr(GratingID)
        self.ser.write(Command.encode('utf-8'))
        self.IsFinished()  
        self.ser.close()
        return

    def SlitAdjust(self, SlitWidth):
        SlitWidth = int(SlitWidth)
        Command_Slit = SlitWidth.to_bytes(2,'big')
        # print(Command_Slit)

        # To DK240/480: <14> SLTADJ
        self.ser.open()
        Command = chr(14)
        self.ser.write(Command.encode('utf-8'))
        self.IsSend(Command)

        # To DK240/480:
        self.ser.write(Command_Slit)
        self.IsFinished_Slit(SlitWidth)
        self.ser.close()
        return
    
    def Test(self):
        # To DK240/480: <17> TEST
        self.ser.open()
        Command = chr(17)
        self.ser.write(Command.encode('utf-8')) 
        self.IsFinished()
        self.ser.close()
        return
    
    def GoTo(self, Wavelength):
        # To DK240/480: <16>
        # To DK240/480: <High Byte> <Mid Byte> <Low Byte>
        self.ser.open()
        High, Mid, Low = self.WavelengthConvert(Wavelength)
        Command_WL = bytes([High, Mid, Low])
        Command = chr(16)
        self.ser.write(Command.encode())
        self.IsSend(Command)
        self.ser.write(Command_WL)
        self.IsFinished()
        self.ser.close()
        return

    def IsSend(self, Command):
        while True:
            # time.sleep(REFLESH_SERIAL_READ)
            result = self.ser.readline()
            # print(result)
            result_int = binary_to_string_UTF(result)
            # print(result_int)
            Command_int = ord(Command)
            time.sleep(2)
            print(result_int)
            if Command_int == result_int:
                break

    def IsFinished(self):
        global Flag_Finished
        Flag_Finished = True
        
        while  Flag_Finished:
            # To DK240/480: <27> ECHO
            Command = chr(27)
            time.sleep(2)
            self.ser.write(Command.encode())
            # time.sleep(REFLESH_SERIAL_READ)
            result = self.ser.readline()
            print(result)
            result_int = binary_to_string_ShiftJis(result)
            print(result_int)
            
            if 24 == result_int:
                print(result_int)
                print('Finished')
                Flag_Finished = False
                break
            
            if 27 == result_int:
                print(result_int)
                print('Finished')
                Flag_Finished = False
                break
        return Flag_Finished
    
    def IsFinished_Slit(self, SlitWidth):
        global Flag_Finished
        Flag_Finished = True
        
        while  Flag_Finished:
            # To DK240/480: <27> ECHO
            Command = chr(30)
            time.sleep(2)
            self.ser.write(Command.encode())
            # time.sleep(REFLESH_SERIAL_READ)
            result = self.ser.readline()
            # print(str(result))
            result_int = binary_to_string(result)
            # print(result_int)
            
            if 'x18' in str(result):
                print(result)
                print('Finished')
                Flag_Finished = False
                break
        return
