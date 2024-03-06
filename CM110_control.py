# -*- coding: utf-8 -*-
"""
Created on Sat Mar 6 08:28:22 2024
@author: Daiki Okazaki @ Laser 
"""
#%%
import time
import serial
from serial.tools import list_ports
import numpy as np
import threading

REFRESH_SERIAL_READ = 1e-4
WAIT_TIME = 1e-1

class CM110Control:
    def __init__(self, port, baudrate=9600):
        self.ser = serial.Serial()
        self.ser.baudrate = baudrate
        self.ser.port = port
        self.ser.rtscts = True
        self.ser.dsrdtr = False
        self.ser.timeout = 2 * REFRESH_SERIAL_READ
    
    @staticmethod
    def list_devices():
        ports = list_ports.comports()
        devices = [info.device for info in ports]
        if not devices:
            print("エラー: ポートが見つかりませんでした")
            return None
        return devices

    def connect(self):
        try:
            self.ser = serial.Serial(self.ser.port,  baudrate=9600, bytesize=8, parity='N', stopbits=1, timeout=self.ser.timeout)
            print(f"Device {self.ser.port} connected successfully.")
        except serial.SerialException as e:
            print("エラー：ポートが開けませんでした。", e)
            return False
        return True

    def disconnect(self):
        if self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")
        else:
            print("Serial connection was close.")

    def binary_to_string(self, binary_data, encoding='shift-jis'):
        try:
            return binary_data.decode(encoding, 'replace')
        except UnicodeDecodeError:
            return ''

    class DeviceOperation:
        def __init__(self, serial_connection):
            self.ser = serial_connection
            self.flag_finished = False
            self.response_received = False
            self.flag_timeout = False
            
        def binary_to_string_UTF(self, binary_data):
            try:
                return ord(binary_data.strip().decode('utf-8'))
            except Exception as e:
                print(f"Error converting binary to UTF-8 string: {e}")
                return None

        def binary_to_string_ShiftJis(self, binary_data):
            try:
                return ord(binary_data.strip().decode('shift-jis'))
            except Exception as e:
                print(f"Error converting binary to Shift-JIS string: {e}")
                return None
        
        def open_serial_connection(self):
            if not self.ser.is_open:
                self.ser.open()

        def close_serial_connection(self):
            if self.ser.is_open:
                self.ser.close()

        def send_command(self, command):
            self.open_serial_connection()
            self.ser.write(command.encode('utf-8'))
            time.sleep(0.1)

        #! Need to add the operation when ths grating is same ord in binary_to_string_UTF does not work().
        def is_finished(self, timeout):
            self.flag_timeout = False
            start_time = time.time()
            while self.flag_finished:
                if time.time() - start_time > timeout:
                    print("Timeout: No response received.")
                    self.flag_timeout = True
                    self.flag_finished = False
                    break

                result = self.ser.readline()
                print(result)
                if result:
                    result_int = self.binary_to_string_UTF(result)
                    if 24 == result_int:  # Assuming 24 is the expected response code
                        self.response_received = True
                        self.flag_finished = False
                        # print('IsFinished OK')

        #! Need to change for CM110.
        @staticmethod
        def wavelength_convert(wavelength):
            # Convert wavelength to an integer and then to a hexadecimal string, removing the '0x' prefix.
            wavelength_int = int(wavelength * 100)
            hex_str = format(wavelength_int, '06x')  # Ensure the hex string is padded to 6 characters.
            # Extract high, mid, and low bytes from the hex string.
            high, mid, low = (int(hex_str[i:i+2], 16) for i in range(0, 6, 2))
            return high, low

        def grating_select(self, GratingID,):        #? To DK240/480: <26> GRTSEL
            self.flag_finished = True
            self.response_received = False
            if not self.ser.isOpen():
                self.ser.open()
            command_prefix = chr(26)
            command = chr(GratingID)
            command_send = command_prefix + command

            is_finished_thread = threading.Thread(target=self.is_finished, args=(12.5,))
            is_finished_thread.start()
            time.sleep(0.1)
            self.ser.write(command_send.encode('utf-8'))
            is_finished_thread.join()
            self.ser.close()
            return

        #! Need to confirm the format of 'high & low', 'command send'.
        def go_to(self, Wavelength, timeout=5):
            self.flag_finished = True
            self.response_received = False
            if not self.ser.isOpen(): # Ensure the serial port is open
                self.ser.open()

            command_prefix = chr(16)
            high, low = self.wavelength_convert(Wavelength)
            command_WL = bytes([high, low])
            command_send = command_prefix.encode('utf-8') + command_WL

            is_finished_thread = threading.Thread(target=self.is_finished, args=(timeout,))  # chr(26) is the command to be sent
            is_finished_thread.start()
            time.sleep(0.1)
            self.ser.write(command_send)
            is_finished_thread.join()
            self.ser.close()
            return

if __name__ == '__main__':
    CM110_control = CM110Control("COM5", 9600)
    if CM110_control.connect():
        device_op = CM110_control.DeviceOperation(CM110_control.ser)
        device_op.grating_select(1)  # Example of selecting grating 1
        # device_op.go_to(4500)  # Example of moving to 500 nm wavelength
        CM110_control.disconnect()
        pass
# %%