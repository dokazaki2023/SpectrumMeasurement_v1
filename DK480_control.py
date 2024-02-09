# -*- coding: utf-8 -*-
"""
Created on Sat May 27 08:28:22 2023

@author: Daiki Okazaki @ Laser 
"""

#%%
import time
import serial
from serial.tools import list_ports
import numpy as np
import threading

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
        self.flag_finished = False
        self.response_received = False
        self.flag_timeout = False

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

    def GratingSelect(self, GratingID,):        #? To DK240/480: <26> GRTSEL
        # Ensure the serial port is open
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        Command = chr(26)
        # Start IsSend in a separate thread to listen for responses before sending the command
        is_send_thread = threading.Thread(target=self.IsSend, args=(Command,))  # chr(26) is the command to be sent
        is_send_thread.start()
        # Allow a very short delay to ensure the thread is listening # Adjust this value as needed; it should be as short as possible
        time.sleep(0.1)
        # Send the command
        self.ser.write(Command.encode('utf-8'))
        # Wait for the IsSend thread to finish
        is_send_thread.join()
        self.ser.close()

        #? To DK240/480: One Byte Grating ID
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        Command = chr(GratingID)
        is_finished_thread = threading.Thread(target=self.IsFinished, args=(150,))  # chr(26) is the command to be sent
        is_finished_thread.start()
        time.sleep(0.1)
        self.ser.write(Command.encode('utf-8'))
        is_finished_thread.join()
        self.ser.close()
        return
    
    def GoTo(self, Wavelength):
        #? To DK240/480: <16> # To DK240/480: <High Byte> <Mid Byte> <Low Byte>
        if not self.ser.isOpen(): # Ensure the serial port is open
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        High, Mid, Low = self.WavelengthConvert(Wavelength)
        Command_WL = bytes([High, Mid, Low])
        Command = chr(16)
        # Start IsSend in a separate thread to listen for responses before sending the command
        is_send_thread = threading.Thread(target=self.IsSend, args=(Command,))  # chr(26) is the command to be sent
        is_send_thread.start()
        # Allow a very short delay to ensure the thread is listening # Adjust this value as needed; it should be as short as possible
        time.sleep(0.1)  
        # Send the command
        self.ser.write(Command.encode('utf-8'))
        # Wait for the IsSend thread to finish
        is_send_thread.join()
        self.ser.close()
        
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        
        is_finished_thread = threading.Thread(target=self.IsFinished, args=(20,))  # chr(26) is the command to be sent
        is_finished_thread.start()
        time.sleep(0.1)
        self.ser.write(Command_WL)
        is_finished_thread.join()
        self.ser.close()
        return

    def IsSend(self, Command):
        start_time = time.time()  # Record the start time
        timeout = 2  # Timeout in seconds
        while self.flag_finished:
            if time.time() - start_time > timeout:
                print("Timeout: No response received.")
                self.flag_timeout = True
                self.flag_finished = False  # Exit the loop after the timeout
                break
        
            result = self.ser.readline()
            if result:
                result_int = binary_to_string_UTF(result)
                Command_int = ord(Command)
                if Command_int == result_int:
                    self.response_received = True
                    self.flag_finished = False
                    # print('IsSend OK')

    def IsFinished(self, timeout):
        self.flag_timeout = False
        start_time = time.time()  # Record the start time
        while self.flag_finished:
            if time.time() - start_time > timeout:
                print("Timeout: No response received.")
                self.flag_timeout = True
                self.flag_finished = False  # Exit the loop after the timeout
                break
            result = self.ser.readline()
            if result:
                result_int = binary_to_string_ShiftJis(result)
                if 24 == result_int:
                    self.response_received = True
                    self.flag_finished = False
                    print('IsFinished OK')

    def PreCheck(self):
        #? To DK240/480: <27> ECHO # Ensure the serial port is open
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        Command = chr(27)
        # Start IsSend in a separate thread to listen for responses before sending the command
        is_send_thread = threading.Thread(target=self.IsSend, args=(Command,))  # chr(27) is the command to be sent
        is_send_thread.start()
        # Allow a very short delay to ensure the thread is listening # Adjust this value as needed; it should be as short as possible
        time.sleep(0.1)  
        # Send the command
        self.ser.write(Command.encode('utf-8'))
        # Wait for the IsSend thread to finish
        is_send_thread.join()
        self.ser.close()
        return

    def SlitAdjust(self, SlitWidth):
        SlitWidth = int(SlitWidth)
        Command_Slit = SlitWidth.to_bytes(2,'big')
        #? To DK240/480: <14> SLTADJ # Ensure the serial port is open
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        Command = chr(14)
        # Start IsSend in a separate thread to listen for responses before sending the command
        is_send_thread = threading.Thread(target=self.IsSend, args=(Command,))  # chr(26) is the command to be sent
        is_send_thread.start()
        # Allow a very short delay to ensure the thread is listening # Adjust this value as needed; it should be as short as possible
        time.sleep(0.1)  
        # Send the command
        self.ser.write(Command.encode('utf-8'))
        # Wait for the IsSend thread to finish
        is_send_thread.join()
        self.ser.close()
        
        #? To DK240/480:
        if not self.ser.isOpen():
            self.ser.open()
        # Initialize the flag to indicate the thread should listen for a response
        self.flag_finished = True
        self.response_received = False
        
        is_finished_thread = threading.Thread(target=self.IsFinished, args=(20,))  # chr(26) is the command to be sent
        is_finished_thread.start()
        time.sleep(0.1)  
        self.ser.write(Command_Slit)
        is_finished_thread.join()
        self.ser.close()
        return


if __name__ == '__main__':
    inst_DK = Connect()
    DK = DK480(inst_DK)
    DK.Test()
    # DK.GratingSelect(3)
    # DK.SlitAdjust(200)
    # DK.GoTo(3500)
