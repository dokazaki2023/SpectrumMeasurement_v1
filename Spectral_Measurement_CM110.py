#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 5 14:00:25 2024
@author: okazakidaiki
"""
#%%
from PyQt5.QtWidgets import QButtonGroup, QFileDialog, QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, Qt, QThreadPool, pyqtSlot
import pyqtgraph.exporters # pg.exporters を呼ぶために必要
import CM110_control, SDS2352X_control
import matplotlib.pyplot as plt
from PyQt5 import uic
from pyqtgraph import Point
from functools import partial
from optics import *
from serial.tools import list_ports
import pyqtgraph as pg
import pandas as pd
import numpy as np
import serial
import DK480_control
import datetime
import pyvisa
import threading
import time
import uuid
import sys
import os

# REFRESH_SERIAL_READ = 1e-4
# WAIT_TIME = 1e-1
class MainWindow(QMainWindow):
    SPEED_OF_LIGHT = 2.997924 * 10**8
    
    def __init__(self):
        super().__init__()
        global times
        times = 0
        
        self.WL_Target = 0
        self.WL_Start = 0
        self.WL_Stop = 0
        self.GratingID = 2
        self.Groove = 150
        self.Slit = 100

        self.setupDialogs()
        self.setupThreadPool()
        self.setupDefaultValues()
        self.setupConnections()
        self.setupGraphs()
        self.dlg1.show()
        
    def setupDialogs(self):
        self.dlg1 = uic.loadUi("CM110.ui")
        
    def setupThreadPool(self):
        self.threadpool = QThreadPool()
        self.x = {}
        self.y = {}
        self.lines = {}
        self.color_index = 0
        
    def setupDefaultValues(self):
        # Example: Set default values for dlg1's line edits
        defaults = {
            "LineEdit_Folders": "C:\\Users\\okazaki\\Desktop\\実験データ\\",
            "LineEdit_Data_Number": '0',
            "LineEdit_Target_WL": '3400',
            "LineEdit_Start_WL": '3800',
            "LineEdit_Stop_WL": '4000',
            "LineEdit_Target_WN": '',
            "LineEdit_Start_WN": '',
            "LineEdit_Stop_WN": '',
            "LineEdit_Step_WL": '5',
            "LineEdit_Sampling_Rate": 'Not Ready',
            "LineEdit_Sampling_Number": 'Not Ready',
        }
        for line_edit, value in defaults.items():
            getattr(self.dlg1, line_edit).setText(value)
        
    ## Toggle Button ##
    def setupConnections(self):
        # Combo Boxes
        combo_boxes = {
            "ComboBox_Repetition": self.repetition,
            "ComboBox_Math_Range": self.math_range,
        }
        for box_name, function in combo_boxes.items():
            getattr(self.dlg1, box_name).activated[str].connect(function)

        # Push Buttons
        push_buttons = {
            "Button_Close": self.close_application,
            "Button_Folder": self.folder_choose,
            "Button_Go": self.Go,
            "Button_Measure": self.execute,
            "Button_Update": self.update,
            "Button_Previous": self.AddPlot,
            "Button_Delete": self.DeletePlot,
        }
        for btn_name, function in push_buttons.items():
            if hasattr(self.dlg1, btn_name):
                getattr(self.dlg1, btn_name).clicked.connect(function)
            elif hasattr(self.dlg2, btn_name):  # For dlg2 specific buttons
                getattr(self.dlg2, btn_name).clicked.connect(function)

        # Radio Buttons
        btngroup_Grating = QButtonGroup()
        for i in range(1, 3):
            radio_button = getattr(self.dlg1, f'radioButton{i}')
            btngroup_Grating.addButton(radio_button)
            # radio_button.toggled.connect(lambda checked, b=i: self.btnstate(radio_button) if checked else None)
            radio_button.toggled.connect(partial(self.btnstate, radio_button))

    def setupGraphs(self):
        self.configurePlot(self.dlg1.graphicsView1.plotItem)
        self.configurePlot(self.dlg1.graphicsView2.plotItem)
    
    def configurePlot(self, plotItem, logModeY=False):
        font = 'Yu Gothic UI'
        plotItem.setLabel('bottom', f'<font face="{font}">Wavelength (nm)</font>')
        plotItem.setLabel('left', f'<font face="{font}">Power spectrum (a.u.)</font>')
        axisPen = pg.mkPen(color='w', width=1.0)
        plotItem.getAxis('bottom').setPen(axisPen)
        plotItem.getAxis('left').setPen(axisPen)
        font_obj = QtGui.QFont(font)
        plotItem.getAxis("left").tickFont = font_obj
        plotItem.getAxis("bottom").tickFont = font_obj
        plotItem.setLogMode(False, logModeY)
    
    def update(self):
        # Update instance attributes from UI inputs
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        self.WL_Start = float(self.dlg1.LineEdit_Start_WL.text())
        self.WL_Stop = float(self.dlg1.LineEdit_Stop_WL.text())
        self.WL_step = float(self.dlg1.LineEdit_Step_WL.text())
        # Update UI with calculated wavenumbers
        for attr_name, WL_value in [("LineEdit_Target_WN", self.WL_Target), ("LineEdit_Start_WN", self.WL_Start), ("LineEdit_Stop_WN", self.WL_Stop)]:
            wavenumber = self.calculate_wavenumber(WL_value)
            if wavenumber is not None:
                getattr(self.dlg1, attr_name).setText(str(wavenumber))
    
    def calculate_wavenumber(self, wavelength):
        try:
            return np.round(1 / (wavelength * 1e-7), 2)
        except Exception as e:
            print(f"Error calculating wavenumber: {e}")
            return None
    
    def keyPressEvent(self, event): # エスケープキーを押すと画面が閉じる
        if event.key() == Qt.Key_Escape:
            self.close_application()
    
    def close_application(self):
        self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The Application is closed')
        self.dlg1.close()  
        print('Turned off')
        self.close()  # Close the application window
        
    def folder_choose(self):
        global file_path
        file_path = QFileDialog.getExistingDirectory()
        if len(file_path) == 0:
            return
        file_path = file_path.replace('/', chr(92))+chr(92)
        self.dlg1.textEdit.append('Path: ' + file_path) # 文字を表示する
        self.dlg1.LineEdit_Folders.setText(str(file_path))

    def btnstate(self,radio_button, checked):
        if not checked:
            return  # Ignore signal if button is being unchecke
        
        CM.precheck()
        if radio_button.isChecked():
            # Example action based on the specific radio button checked
            if radio_button == self.dlg1.radioButton1:
                self.GratingID = 1
                self.Groove = 600
                print (self.dlg1.radioButton1.text()+" is selected")
            elif radio_button == self.dlg1.radioButton2:
                self.GratingID = 2
                self.Groove = 150
                print (self.dlg1.radioButton2.text()+" is selected")
        CM.grating_select(self.GratingID)

        if CM.flag_timeout:
            self.timeout_notification()
        else:
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Grating is successfully changed to the Grating ' + str(self.GratingID)) # 文字を表示する
            self.dlg1.textEdit.show()

    def Go(self):
        CM.precheck()
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        CM.go_to(self.WL_Target, timeout=50)
        if CM.flag_timeout:
            self.timeout_notification()
        else:
            print('Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm')
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm') # 文字を表示する
            self.dlg1.textEdit.show()
            
    def timeout_notification(self):
        redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : Timeout occurs ! ' + "</span>"
        self.dlg1.textEdit.append(redText)

    def write_command_and_log(self, setting_type, text, command_map):
        command = command_map.get(text)
        if command:
            inst_SDS.write(command)
            message = f"{datetime.datetime.now()} : {setting_type} : {text} is selected"
            self.dlg1.textEdit.append(message)  # GUI log for user information
            self.dlg1.textEdit.show()
        else:
            print(f"Unrecognized {setting_type.lower()} setting: {text}")

    def repetition(self, text):
        repetition_map = {
            '10 Hz': "tdiv 0.2",
            '100 Hz': "tdiv 0.02"
        }
        self.write_command_and_log("Repetition Rate", text, repetition_map)

    def math_range(self, text):
        math_range_map = {
            '10 mV^2': "mtvd 10mV",
            '20 mV^2': "mtvd 20mV",
            '50 mV^2': "mtvd 50mV",
            '100 mV^2': "mtvd 100mV",
            '200 mV^2': "mtvd 200mV",
            '500 mV^2': "mtvd 500mV",
            '1 V^2': "mtvd 1000mV",
            '2 V^2': "mtvd 2000mV",
            '5 V^2': "mtvd 5000mV",
            '10 V^2': "mtvd 10000mV",
            '20 V^2': "mtvd 20000mV",
            '50 V^2': "mtvd 50000mV"
        }
        self.write_command_and_log("Math Range", text, math_range_map)

    def AddPlot(self):
        filename = str(self.dlg1.LineEdit_Folders2.text())
        df = pd.read_csv(filename)
        x = df.wavelength.values
        y = df.rawdata.values
        self.dlg1.graphicsView2.plotItem.addItem(
            pg.PlotCurveItem(x=x, y=y, pen = pg.mkPen(pyqtgraph.hsvColor(hue=self.color_index/5, sat=1.0, val=1.0, alpha=1.0), 
                                                        style = Qt.SolidLine), antialias = True))
        self.color_index += 1
        if self.color_index > 5:
            self.color_index = 0
        
    def DeletePlot(self):
        self.dlg1.graphicsView2.clear()

    def execute(self):
        self.dlg1.graphicsView1.clear()
        CM.precheck()
        worker = Worker()
        worker.signals.data.connect(self.receive_data)
        self.threadpool.start(worker) # Execute

    def receive_data(self, data):
        worker_id, x, y = data
        if worker_id not in self.lines:
            self.x[worker_id] = [x]
            self.y[worker_id] = [y]
            self.lines[worker_id] = self.dlg1.graphicsView1.plot(self.x[worker_id],self.y[worker_id])
            return
        self.x[worker_id].append(x) # Update existing plot/data
        self.y[worker_id].append(y)
        self.lines[worker_id].setData(self.x[worker_id], self.y[worker_id])

class WorkerSignals(QObject):
    data = pyqtSignal(tuple)
class Worker(QRunnable):
    def __init__(self):
        super().__init__()
        self.worker_id = uuid.uuid4().hex  # Unique ID for this worker.
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        global times
        
        def duplicate_rename(filename):
            new_name = filename
            global times
            if os.path.exists(filename):
                name, ext = os.path.splitext(filename)
                while True:
                    new_name = "{}{}({}){}".format(directory, '_Spectrum', times, ext)
                    if not os.path.exists(new_name):
                        return new_name
                    times += 1
                    window.dlg1.LineEdit_Data_Number.setText(str(times))
            else:
                return new_name
        
        def generate_and_rename_filenames(directory, base_name, times, extensions):
            filenames = []
            for ext in extensions:
                filename = f"{directory}{base_name}({times}){ext}" # Generate the initial filename
                filename = duplicate_rename(filename) # Rename the file if it already exists to ensure uniqueness
                filenames.append(filename) # Append the possibly renamed filename to the list

            return filenames
        
        window.update()
        WL = window.WL_Start
        Wavelength = window.WL_Start
        Spectrum = 0
        vdiv_float, ofst_float = SDS.query_param_math()
        SDS.set_datasize(7)
        while WL <= window.WL_Stop:
            # DK.precheck()
            CM.go_to(WL)
            data = SDS.get_math(vdiv_float, ofst_float)
            Data_Mean = np.average(data)
            self.signals.data.emit((self.worker_id, WL, Data_Mean))  
            WL = WL + window.WL_step
            Wavelength = np.r_[WL, Wavelength]
            Spectrum = np.r_[Data_Mean, Spectrum]
            
        # ## save datas
        dammy = np.zeros(len(Wavelength))
        folder = str(window.dlg1.LineEdit_Folders.text())
        savedata = np.array([dammy.T,Wavelength,Spectrum])
        saves = savedata.transpose()
        folder = str(window.dlg1.LineEdit_Folders.text())
        directory = folder + str(datetime.date.today())
        base_name = "_Spectrum"
        extensions = ['.csv', '.png', '.txt']
        filenames = generate_and_rename_filenames(directory, base_name, times, extensions)

        try:
            np.savetxt(filenames[0], saves, fmt="%.10f",delimiter=",",header="dammy,wavelength,rawdata")# 保存する文字列。
            exporter = pg.exporters.ImageExporter(window.dlg1.graphicsView1.scene()) # exportersの直前に pg.QtGui.QApplication.processEvents() を呼ぶ！
            exporter.parameters()['width'] = 1000
            exporter.export(filenames[1])
            window.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Measurement No.'+str(int(window.dlg1.LineEdit_Data_Number.text()))+ ' is saved successefully')
            times = int(window.dlg1.LineEdit_Data_Number.text()) + 1 # measurement number
            window.dlg1.LineEdit_Data_Number.setText(str(times))
            text = str(window.dlg1.textEdit.toPlainText())
            with open(filenames[2], 'w') as f:
                f.write(text)
            print('ファイルは正常に保存されました。')
        except:
            print('ファイルの保存に失敗しました。')
            redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : ERROR: Data saving failed ' + "</span>"
            window.dlg1.textEdit.append(redText)
        window.dlg1.textEdit.show()


if __name__ == '__main__':
    CM110_control = CM110_control.CM110Control(port="COM5", baudrate=9600)
    if CM110_control.connect():
        CM = CM110_control.DeviceOperation(CM110_control.ser)
        CM110_control.disconnect()
    
        inst_SDS = SDS2352X_control.connect('USB0::0xF4EC::0x1010::SDS2EDDD7R1135::INSTR')
        SDS = SDS2352X_control.Oscilloscope(inst_SDS)
        pass
    
    app = QApplication(sys.argv)
    window = MainWindow()
    app.exec_()
    
# %%
