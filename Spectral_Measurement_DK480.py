#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 14:00:25 2022

@author: okazakidaiki
"""
#%%
from PyQt5.QtWidgets import QButtonGroup, QFileDialog, QMainWindow, QApplication, QMessageBox
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, Qt, QThreadPool, pyqtSlot
import pyqtgraph.exporters # pg.exporters を呼ぶために必要
from PyQt5 import uic
from pyqtgraph import Point
from optics import *
import pyqtgraph as pg
import pandas as pd
import numpy as np
import DK480_control
import datetime
import uuid
import sys
import os

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
        self.Groove = 300
        
        self.Slit = 100
        self.dlg1 = uic.loadUi("DK480.ui")
        self.dlg2 = uic.loadUi("DK480_Raytrace.ui")

        self.setupDialogs()
        self.setupThreadPool()
        self.setupDefaultValues()
        self.setupConnections()
        self.setupGraphs()
        self.dlg1.show()
        
    def setupDialogs(self):
        self.dlg1 = uic.loadUi("DK480.ui")
        self.dlg2 = uic.loadUi("DK480_Raytrace.ui")
        
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
            "LineEdit_Entrance": '100',
            "LineEdit_Resolution_Wavenumber": '',
            "LineEdit_Resolution_Frequency": '',
            "LineEdit_Resolution_Wavelength": '',
            "LineEdit_Target_WL": '3400',
            "LineEdit_Start_WL": '3500',
            "LineEdit_Stop_WL": '3550',
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
            "ComboBox_DR": self.DynamicReserve,
            "ComboBox_IntegrationTime": self.Integration,
            "ComboBox_Sensitivity": self.Sensitivity,
        }
        for box_name, function in combo_boxes.items():
            getattr(self.dlg1, box_name).activated[str].connect(function)

        # Check Box
        self.dlg1.CheckBox_LockIn.stateChanged.connect(
            lambda state: self.LockIn(self.dlg1.CheckBox_LockIn.checkState()))

        # Push Buttons
        push_buttons = {
            "Button_Close": self.close_application,
            "Button_Folder": self.folder_choose,
            "Button_Change_Slit": self.ChangeSlit,
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
        for i in range(1, 4):
            radio_button = getattr(self.dlg1, f'radioButton{i}')
            btngroup_Grating.addButton(radio_button)
            radio_button.toggled.connect(lambda checked, b=i: self.btnstate(radio_button) if checked else None)

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
        
    def calculate_resolution(self, WL_Target, Slit, Groove):
        try:
            Resolution_Slit = WL_Target * Slit / 1e6
            Resolution_Grating = WL_Target / (Groove * 60)
            Resolution_WL = np.sqrt(Resolution_Slit**2 + Resolution_Grating**2)
            Resolution_Frequency = (self.SPEED_OF_LIGHT * (Resolution_WL * 1e-9) / ((WL_Target * 1e-9)**2))
            Resolution_WN = Resolution_Frequency / (self.SPEED_OF_LIGHT * 1e2)
            return np.round(Resolution_WL, 3), np.round(Resolution_Frequency * 1e-9, 3), np.round(Resolution_WN, 3)
        except Exception as e:
            # Optionally log the error
            print(f"Error calculating resolution: {e}")
            return None, None, None
    
    def update(self):
        # Update instance attributes from UI inputs
        self.Slit = float(self.dlg1.LineEdit_Entrance.text())
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        self.WL_Start = float(self.dlg1.LineEdit_Start_WL.text())
        self.WL_Stop = float(self.dlg1.LineEdit_Stop_WL.text())
        self.WL_step = float(self.dlg1.LineEdit_Step_WL.text())
        # Perform resolution calculation
        Resolution_WL, Resolution_Frequency, Resolution_WN = self.calculate_resolution(self.WL_Target, self.Slit, self.Groove)

        if Resolution_WL is not None:
            self.dlg1.LineEdit_Resolution_Wavelength.setText(str(Resolution_WL))
            self.dlg1.LineEdit_Resolution_Wavenumber.setText(str(Resolution_WN))
            self.dlg1.LineEdit_Resolution_Frequency.setText(str(Resolution_Frequency))
            self.dlg1.textEdit.show()

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
            
    def close_application2(self):
        self.dlg2.close()  
        
    def folder_choose(self):
        global file_path
        file_path = QFileDialog.getExistingDirectory()
        if len(file_path) == 0:
            return
        file_path = file_path.replace('/', chr(92))+chr(92)
        self.dlg1.textEdit.append('Path: ' + file_path) # 文字を表示する
        self.dlg1.LineEdit_Folders.setText(str(file_path))
    
    def btnstate(self,radio_button):
        DK.precheck()
        if radio_button.isChecked():
            # Example action based on the specific radio button checked
            if radio_button == self.dlg1.radioButton1:
                self.GratingID = 1
                self.Groove = 1200
                print (self.dlg1.radioButton1.text()+" is selected")
            elif radio_button == self.dlg1.radioButton2:
                self.GratingID = 2
                self.Groove = 600
                print (self.dlg1.radioButton2.text()+" is selected")
            elif radio_button == self.dlg1.radioButton3:
                self.GratingID = 3
                self.Groove = 300
                print (self.dlg1.radioButton3.text()+" is selected")
            else:
        DK.grating_select(self.GratingID)
        print(self.GratingID)
        
        if DK.flag_timeout:
            self.timeout_notification()
        else:
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Grating is successfully changed to the Grating ' + str(self.GratingID)) # 文字を表示する
            self.dlg1.textEdit.show()


    def ChangeSlit(self):
        if float(self.dlg1.LineEdit_Entrance.text()) == self.Slit:
            return
        else:
            DK.precheck()
            self.Slit = float(self.dlg1.LineEdit_Entrance.text())
            DK.slit_adjust(self.Slit)
            if DK.flag_timeout:
                self.timeout_notification()
            else:
                self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Entrance slit is set to ' + str(self.Slit) + ' um') # 文字を表示する
                self.dlg1.textEdit.show()
            
    def Go(self):
        DK.precheck()
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        DK.go_to(self.WL_Target)
        if DK.flag_timeout:
            self.timeout_notification()
        else:
            print('Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm')
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm') # 文字を表示する
            self.dlg1.textEdit.show()
            
    def timeout_notification(self):
        redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : Timeout occurs ! ' + "</span>"
        self.dlg1.textEdit.append(redText)
        
########################################################
########################################################
    def LockIn(self,state):
        if state == Qt.Checked:
            import LI5640_control # visaの取
            self.inst_LI = LI5640_control.connect('GPIB0::2::INSTR')
            self.LIA1 = LI5640_control.Lockin(self.inst_LI)
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Lock-In amplifier is connected') # 文字を表示する
            self.dlg1.textEdit.show() 
            print('Lock in measurement system is ready')
    
    def write_command_and_log(self, setting_type, text, command_map):
        command = command_map.get(text)
        if command:
            self.inst_LI.write(command)
            message = f"{datetime.datetime.now()} : {setting_type} : {text} is selected"
            print(message)  # Console log for debugging or info
            self.dlg1.textEdit.append(message)  # GUI log for user information
            self.dlg1.textEdit.show()
        else:
            print(f"Unrecognized {setting_type.lower()} setting: {text}")

    def DynamicReserve(self, text):
        dynamic_reserve_map = {
            'LOW': "DRSV 2",
            'MIDDLE': "DRSV 1",
            'HIGH': "DRSV 0",
        }
        self.write_command_and_log("Dynamic Reserve", text, dynamic_reserve_map)

    def Integration(self, text):
        integration_map = {
            '1 ms': "TCON 4",
            '3 ms': "TCON 5",
            '10 ms': "TCON 6",
            '30 ms': "TCON 7",
            '100 ms': "TCON 8",
            '300 ms': "TCON 9",
            '1000 ms': "TCON 10",
        }
        self.write_command_and_log("Time constant", text, integration_map)

    def Sensitivity(self, text):
        sensitivity_map = {
            '1 V': "VSEN 26",
            '500 mV': "VSEN 25",
            '200 mV': "VSEN 24",
            '100 mV': "VSEN 23",
            '50 mV': "VSEN 22",
            '20 mV': "VSEN 21",
            '10 mV': "VSEN 20",
            '5 mV': "VSEN 19",
            '2 mV': "VSEN 18",
            '1 mV': "VSEN 17",
            '500 uV': "VSEN 16",
            '200 uV': "VSEN 15",
            '100 uV': "VSEN 14",
            '50 uV': "VSEN 13",
            '20 uV': "VSEN 12",
            '10 uV': "VSEN 11",
            '5 uV': "VSEN 10",
            '2 uV': "VSEN 9",
            '1 uV': "VSEN 8",
            '500 nV': "VSEN 7",
            '200 nV': "VSEN 6",
            '100 nV': "VSEN 5",
        }
        self.write_command_and_log("Sensitivity", text, sensitivity_map)

########################################################
########################################################
    def BG(self):
        global BG
        BG_data = []
        for i in range (100):
            self.LIA1.prepare_R()
            self.LIA1.trigger()
            BG_now = self.LIA1.get_R()
            BG_data.append(BG_now)
        BG = np.average(BG_data)
        self.dlg1.textEdit.append('BG measurement is finished')
        
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
        DK.precheck()
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
        window.LIA1.prepare_R()
        window.LIA1.trigger()
        while WL <= window.WL_Stop:
            # DK.precheck()
            DK.go_to(WL)
            data = window.LIA1.get_R()
            Data_Mean = np.average(data[0])
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
            window.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Measurement No.'+str(int(window.dlg1.LineEdit_Data_Number.text()))+ ' is finished')
            times = int(window.dlg1.LineEdit_Data_Number.text()) + 1 # measurement number
            window.dlg1.LineEdit_Data_Number.setText(str(times))
            text = str(window.dlg1.textEdit.toPlainText())
            with open(filenames[2], 'w') as f:
                f.write(text)
            window.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The datas are saved successefully.') 
            print('ファイルは正常に保存されました。')
        except:
            print('ファイルの保存に失敗しました。')
            redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : ERROR: Data saving failed ' + "</span>"
            window.dlg1.textEdit.append(redText)
        window.dlg1.textEdit.show()

class SubWindow(QMainWindow):
    def __init__(self):
        dlg2 = uic.loadUi("DK480_Raytrace.ui")
        dlg2.graphicsView3.clear()
        dlg2.graphicsView3.plotItem.setRange(xRange = (-500, 100), yRange = (-350, 250), padding = 0)
        WL_Target, WL_BW_nm, Num_color = 4100, 600, 11
        WL_center_um = 1e-3 * WL_Target
        WL_Blue = 1e3 * WL_center_um - WL_BW_nm / 2
        WL_Red = 1e3 * WL_center_um + WL_BW_nm / 2
        start_positions = [-312.5, -309, -316]  # Different start positions for rays

        optics = [
                    Mirror(r1=0, pos=(-2, -315), angle=-135, d1=25, d2=25, d=6, name='Coupling Mirror'),
                    Lens(pos=(0, -225), angle=90, dia=25, r1=100/2, r2=0, d=4.0, glass='CaF2', name='Coupling Lens'),
                    Mirror(r1=0, pos=(2, -85), angle=41.8, d1=25, d2=25, d=6, name='Second Mirror'),
                    Mirror(r1=-480*2, pos=(-450, -40), angle=180, d1=60, d2=60, d=10, name='Collimating Mirror'),
                    Grating(Groove=300, pos=(0, 7), angle=-38.3, d1=68, d2=68, d=10, name='Grating'),
                    Mirror(r1=-480*2, pos=(-450, 40), angle=180, d1=60, d2=60, d=10, name='Focusing Mirror'),
                    Mirror(r1=0, pos=(0, 79), angle=-43.2, d1=25, d2=25, d=6, name='Output Mirror')
                ]
        for o in optics:
            dlg2.graphicsView3.addItem(o) 
        
        all_rays = []
        for start_y in start_positions:
            rays = []
            for wl in np.linspace(WL_Blue, WL_Red, Num_color):
                ray = Ray(start=Point(100, start_y), dir=(-1, 0), wl=wl, WL_min=WL_Blue, WL_max=WL_Red)
                dlg2.graphicsView3.addItem(ray)
                rays.append(ray)
            all_rays.append(rays)
        
        self.tracers = []  # Initialize an empty list to store Tracer instances
        for rays in all_rays:
            tracer = Tracer(rays, optics)
            self.tracers.append(tracer)
        dlg2.show()
        pg.exec()
########################################################
########################################################        
if __name__ == "__main__":
    DK480_control = DK480_control.DK480Control("COM4", 9600)
    if DK480_control.connect():
        DK = DK480_control.DeviceOperation(DK480_control.ser)
        DK480_control.disconnect()
        pass
    app = QApplication(sys.argv)
    window = MainWindow()
    # subWindow = SubWindow()
    app.exec_()

# %%
