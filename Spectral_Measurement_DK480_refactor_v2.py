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
import DK480_control_refactor
import datetime
import uuid
import sys
import os

class MainWindow(QMainWindow):
    def __init__(self, Grating_ID):
        super().__init__()
        global times
        times = 0
        self.WL_Target = 0
        self.WL_Start = 0
        self.WL_Stop = 0
        self.Grating_ID = Grating_ID
        self.Groove = 300
        self.Slit = 100
        
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
        ## Combo ##
        self.dlg1.ComboBox_DR.activated[str].connect(self.DynamicReserve)
        self.dlg1.ComboBox_IntegrationTime.activated[str].connect(self.Integration)
        self.dlg1.ComboBox_Sensitivity.activated[str].connect(self.Sensitivity)
        ## Check Box ##
        self.dlg1.CheckBox_LockIn.stateChanged.connect(lambda: self.LockIn(self.dlg1.CheckBox_LockIn.checkState()))
        ## Push Button ##
        self.dlg1.Button_Close.clicked.connect(self.close_application)
        self.dlg2.Button_Close.clicked.connect(self.close_application2)
        self.dlg1.Button_Folder.clicked.connect(self.folder_choose)
        self.dlg1.Button_Change_Slit.clicked.connect(self.ChangeSlit)
        self.dlg1.Button_Go.clicked.connect(self.Go)
        self.dlg1.Button_Measure.clicked.connect(self.execute)
        self.dlg1.Button_Update.clicked.connect(self.update)
        self.dlg1.Button_Previous.clicked.connect(self.AddPlot)
        self.dlg1.Button_Delete.clicked.connect(self.DeletePlot)
        for i in range(1, 4):
            getattr(self.dlg1, f'radioButton{i}').toggled.connect(lambda _, b=i: self.btnstate(getattr(self.dlg1, f'radioButton{b}')))
        btngroup_Grating = QButtonGroup()
        getattr(self.dlg1, f'radioButton{i}').toggled.connect(lambda _, b=i: self.btnstate(getattr(self.dlg1, f'radioButton{b}')))
        btngroup_Grating.addButton(self.dlg1.radioButton1,1)
        btngroup_Grating.addButton(self.dlg1.radioButton2,1)
        btngroup_Grating.addButton(self.dlg1.radioButton3,1)
        
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
        c = 2.997924*10**(8)
        # Update instance attributes from UI inputs
        self.Slit = float(self.dlg1.LineEdit_Entrance.text())
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        self.WL_Start = float(self.dlg1.LineEdit_Start_WL.text())
        self.WL_Stop = float(self.dlg1.LineEdit_Stop_WL.text())
        
        try:
            Resolution_Slit = self.WL_Target * self.Slit / 1e6
            Resolution_Grating =  self.WL_Target /(Groove*60)
            Resolution_WL = np.sqrt(Resolution_Slit**2 + Resolution_Grating**2)
            Resolution_Frequency = (c*(Resolution_WL*1e-9)/((self.WL_Target*1e-9)**2))
            Resolution_WN = Resolution_Frequency / (c*1e2)
            Resolution_WL = np.round(Resolution_WL,3)
            Resolution_Frequency = np.round(Resolution_Frequency*1e-9,3)
            Resolution_WN = np.round(Resolution_WN,3)
        except:
            return
        self.dlg1.LineEdit_Resolution_Wavelength.setText(str(Resolution_WL))
        self.dlg1.LineEdit_Resolution_Wavenumber.setText(str(Resolution_WN))
        self.dlg1.LineEdit_Resolution_Frequency.setText(str(Resolution_Frequency))
        self.dlg1.textEdit.show()
        
        try:
            # Perform calculations and update UI accordingly
            self.dlg1.LineEdit_Target_WN.setText(str(self.calculate_wavenumber(self.WL_Target)))
            self.dlg1.LineEdit_Start_WN.setText(str(self.calculate_wavenumber(self.WL_Start)))
            self.dlg1.LineEdit_Stop_WN.setText(str(self.calculate_wavenumber(self.WL_Stop)))
        except Exception as e:
            # Handle potential errors, possibly log them or notify the user
            print(f"Error updating wavelengths: {e}")

    def calculate_wavenumber(self, wavelength):
        return np.round(1 / (wavelength * 1e-7), 2)
        
    def keyPressEvent(self, event): # エスケープキーを押すと画面が閉じる
        if event.key() == Qt.Key_Escape:
            self.close_application()
    
    def close_application(self):
        reply = QMessageBox.question(self, 'Confirmation',"Are you sure you want to quit?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
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
    
    def btnstate(self,radioButton):
        global GratingID, Groove
        DK.precheck()
        
        if radioButton.isChecked():
            # Example action based on the specific radio button checked
            if radioButton == self.dlg1.radioButton1:
                self.performActionForRadioButton1()
            elif radioButton == self.dlg1.radioButton2:
                self.performActionForRadioButton2()
            elif radioButton == self.dlg1.radioButton3:
                self.performActionForRadioButton3()
                
        DK.grating_select(self.GratingID)
        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : Timeout occurs ! ' + "</span>"
            self.dlg1.textEdit.append(redText)
        else:
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Grating is successfully changed to the Grating ' + str(self.GratingID)) # 文字を表示する
            self.dlg1.textEdit.show()
                
    def performActionForRadioButton1(self):
        self.GratingID = 1
        self.Groove = 1200
        print (self.dlg1.radioButton1.text()+" is selected")
        pass

    def performActionForRadioButton2(self):
        self.GratingID = 2
        self.Groove = 600
        print (self.dlg1.radioButton1.text()+" is selected")
        pass

    def performActionForRadioButton3(self):
        self.GratingID = 3
        self.Groove = 300
        print (self.dlg1.radioButton1.text()+" is selected")
        pass

    def ChangeSlit(self):
        DK.precheck()
        self.Slit = float(self.dlg1.LineEdit_Entrance.text())
        DK.slit_adjust(self.Slit)
        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : Timeout occurs ! ' + "</span>"
            self.dlg1.textEdit.append(redText)
        else:
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Entrance slit is set to ' + str(self.Slit) + ' um') # 文字を表示する
            self.dlg1.textEdit.show()
        
    def Go(self):
        DK.precheck()
        self.WL_Target = float(self.dlg1.LineEdit_Target_WL.text())
        DK.go_to(self.WL_Target)
        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >" + str(datetime.datetime.now()) + ' : Timeout occurs ! ' + "</span>"
            self.dlg1.textEdit.append(redText)
        else:
            print('Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm')
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Center wavelength is set to ' + str(np.round(self.WL_Target,2)) + ' nm') # 文字を表示する
            self.dlg1.textEdit.show()
            

########################################################
########################################################
    def LockIn(self,state):
        if state == Qt.Checked:
            import LI5640_control_refactor # visaの取
            self.inst_LI = LI5640_control_refactor.connect('GPIB0::2::INSTR')
            self.LIA1 = LI5640_control_refactor.Lockin(self.inst_LI)
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Lock-In amplifier is connected') # 文字を表示する
            self.dlg1.textEdit.show() 
            print('Lock in measurement system is ready')
        
    def DynamicReserve(self,text): 
        if text == 'LOW':
            self.inst_LI.write("DRSV 2") # ダイナミックリザーブ 低 (noisy な時は高く)
        if text == 'MIDDLE':
            self.inst_LI.write("DRSV 1") 
        if text == 'HIGH':
            self.inst_LI.write("DRSV 0") 
        print('Dynamic Reserve : ' + text +' is selected')
        self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Dynamic Reserve : ' + text + ' is selected') # 文字を表示する
        self.dlg1.textEdit.show()  

    def Integration(self,text): 
        if text == '1 ms':
            self.inst_LI.write("TCON 4") # time constant
        if text == '3 ms':
            self.inst_LI.write("TCON 5")
        if text == '10 ms':
            self.inst_LI.write("TCON 6")
        if text == '30 ms':
            self.inst_LI.write("TCON 7")
        if text == '100 ms':
            self.inst_LI.write("TCON 8")
        if text == '300 ms':
            self.inst_LI.write("TCON 9")
        if text == '1000 ms':
            self.inst_LI.write("TCON 10")
        print('Time constant : ' + text +' is selected')
        self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Time constant : ' + text + ' is selected') # 文字を表示する
        self.dlg1.textEdit.show()  

    def Sensitivity(self, text): 
        if text == '1 V':
            self.inst_LI.write("VSEN 26")
        if text == '500 mV':
            self.inst_LI.write("VSEN 25")
        if text == '200 mV':
            self.inst_LI.write("VSEN 24")
        if text == '100 mV':
            self.inst_LI.write("VSEN 23")
        if text == '50 mV':
            self.inst_LI.write("VSEN 22")
        if text == '20 mV':
            self.inst_LI.write("VSEN 21")
        if text == '10 mV':
            self.inst_LI.write("VSEN 20")
        if text == '5 mV':
            self.inst_LI.write("VSEN 19")
        if text == '2 mV':
            self.inst_LI.write("VSEN 18")
        if text == '1 mV':
            self.inst_LI.write("VSEN 17")
        if text == '500 uV':
            self.inst_LI.write("VSEN 16")
        if text == '200 uV':
            self.inst_LI.write("VSEN 15")
        if text == '100 uV':
            self.inst_LI.write("VSEN 14")
        if text == '50 uV':
            self.inst_LI.write("VSEN 13")
        if text == '20 uV':
            self.inst_LI.write("VSEN 12")
        if text == '10 uV':
            self.inst_LI.write("VSEN 11")
        if text == '5 uV':
            self.inst_LI.write("VSEN 10")
        if text == '2 uV':
            self.inst_LI.write("VSEN 9")
        if text == '1 uV':
            self.inst_LI.write("VSEN 8")
        if text == '500 nV':
            self.inst_LI.write("VSEN 7")
        if text == '200 nV':
            self.inst_LI.write("VSEN 6")
        if text == '100 nV':
            self.inst_LI.write("VSEN 5")
        print('Sensitivity : ' + text +' is selected')
        self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Sensitivity : ' + text + ' is selected') # 文字を表示する
        self.dlg1.textEdit.show()       

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
        worker = Worker(self.dlg1)
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
    def __init__(self, dlg):
        super().__init__()
        self.worker_id = uuid.uuid4().hex  # Unique ID for this worker.
        self.signals = WorkerSignals()
        self.dlg1 = dlg
        
    @pyqtSlot()
    def run(self):
        global Wavelength,Spectrum,times,WL
        self.WL_Start = float(self.dlg1.LineEdit_Start_WL.text())
        self.WL_Stop = float(self.dlg1.LineEdit_Stop_WL.text())
        self.WL_step = float(self.dlg1.LineEdit_Step_WL.text())
        # Sampling_Number = float(dlg1.LineEdit_Sampling_Number.text())
        # Sampling_Rate = int(1e3*float(dlg1.LineEdit_Sampling_Rate.text()))     
        
        WL = self.WL_Start
        Wavelength = self.WL_Start
        Spectrum = 0
        self.dlg1.LIA1.prepare_R()
        self.dlg1.LIA1.trigger()
        while WL <= self.WL_Stop:
            DK.precheck()
            DK.go_to(WL)
            data = self.dlg1.LIA1.get_R()
            Data_Mean = np.average(data[0])
            self.signals.data.emit((self.worker_id, WL, Data_Mean))  
            WL = WL + self.WL_step
            Wavelength = np.r_[WL, Wavelength]
            Spectrum = np.r_[Data_Mean, Spectrum]
            
        # ## save datas
        dammy = np.zeros(len(Wavelength))
        folder = str(self.dlg1.LineEdit_Folders.text())
        savedata = np.array([dammy.T,Wavelength,Spectrum])
        saves = savedata.transpose()
        folder = str(self.dlg1.LineEdit_Folders.text())
        directory = folder + str(datetime.date.today())
        
        
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
                    self.dlg1.LineEdit_Data_Number.setText(str(times))
            else:
                return new_name
        
        filename0 = "{}{}({}){}".format(directory, '_Spectrum', times, '.csv')                      
        filename0 = duplicate_rename(filename0)
        filename1 = "{}{}({}){}".format(directory, '_Spectrum', times, '.png')
        filename1 = duplicate_rename(filename1)        
        filename2 = "{}{}({}){}".format(directory, '_Spectrum', times, '.txt')
        filename2 = duplicate_rename(filename2)
        
        try:
            np.savetxt(filename0, saves, fmt="%.10f",delimiter=",",header="dammy,wavelength,rawdata")# 保存する文字列。
            exporter = pg.exporters.ImageExporter(self.dlg1.graphicsView1.scene()) # exportersの直前に pg.QtGui.QApplication.processEvents() を呼ぶ！
            exporter.parameters()['width'] = 1000
            exporter.export(filename1)
            
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Measurement No.'+str(int(self.dlg1.LineEdit_Data_Number.text()))+ ' is finished')
            times = int(self.dlg1.LineEdit_Data_Number.text()) + 1 # measurement number
            self.dlg1.LineEdit_Data_Number.setText(str(times))
            
            text = str(self.dlg1.textEdit.toPlainText())
            with open(filename2, 'w') as f:
                f.write(text)
            self.dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The datas are saved successefully.') 
            print('ファイルは正常に保存されました。')
        except:
            print('ファイルの保存に失敗しました。')
            redText = "<span style=\" color:#ff0000;\" >"
            redText += str(datetime.datetime.now()) + ' : ERROR: Data saving failed '
            redText += "</span>"
            self.dlg1.textEdit.append(redText)
        self.dlg1.textEdit.show()

class SubWindow(QMainWindow):
    def __init__(self):
        global dlg2
        dlg2 = uic.loadUi("DK480_Raytrace.ui")
        dlg2.graphicsView3.clear()
        p3 = dlg2.graphicsView3.plotItem
        p3.setRange(xRange = (-500, 100), yRange = (-350, 250), padding = 0)
        dlg2.show()  # ダイアログ1を表示
        
        optics = []
        allRays1 = []
        allRays2 = []
        allRays3 = []
        Groove = 300
        WL_Target = 4100
        WL_BW_nm = 600
        Num_color = 11
        WL_center_um = 1e-3*WL_Target
        WL_Blue = 1e3*WL_center_um - WL_BW_nm/2
        WL_Red =  1e3*WL_center_um + WL_BW_nm/2
        
        M1 = Mirror(r1=0, pos=(-2, -315), angle=-135, d1=25, d2=25, d=6, name = 'Coupling Mirror')
        L1 = Lens(pos=(0, -225), angle=90, dia=25, r1=100/2, r2= 0, d= 4.0, glass='CaF2', name = 'Coupling Lens')
        M2 = Mirror(r1=0, pos=(2, -85), angle=41.8, d1=25, d2=25, d=6, name = 'Second Mirror')
        P1 = Mirror(r1=-480*2, pos=(-450, -40), angle=180, d1=60, d2=60, d=10, name = 'Collimating Mirror')
        G1 = Grating(Groove=Groove, pos=(0,7), angle=-38.3, d1=68, d2=68, d=10, name = 'Grating')
        P2 = Mirror(r1=-480*2, pos=(-450, 40), angle=180, d1=60, d2=60, d=10, name = 'Focusing Mirror')
        M3 = Mirror(r1=0, pos=(0, 79), angle=-43.2, d1=25, d2=25, d=6, name = 'Output Mirror')
        optics.append(M1)
        optics.append(L1)
        optics.append(M2)
        optics.append(P1)
        optics.append(G1)
        optics.append(P2)
        optics.append(M3)
        
        for wl in np.linspace(WL_Blue, WL_Red, Num_color):
            r1 = Ray(start=Point(100, -312.5), dir=(-1,0), wl=wl, WL_min=WL_Blue, WL_max=WL_Red, Laser='Fe')
            dlg2.graphicsView3.addItem(r1)
            allRays1.append(r1)
        
        for wl in np.linspace(WL_Blue, WL_Red, Num_color):
            r2 = Ray(start=Point(100, -309), dir=(-1,0), wl=wl, WL_min=WL_Blue, WL_max=WL_Red, Laser='Fe')
            dlg2.graphicsView3.addItem(r2)
            allRays2.append(r2)
        
        for wl in np.linspace(WL_Blue, WL_Red, Num_color):
            r3 = Ray(start=Point(100, -316), dir=(-1,0), wl=wl, WL_min=WL_Blue, WL_max=WL_Red, Laser='Fe')
            dlg2.graphicsView3.addItem(r3)
            allRays3.append(r3)
        
        for o in optics:
            dlg2.graphicsView3.addItem(o)  
        tracer1 = Tracer(allRays1, optics)
        tracer2 = Tracer(allRays2, optics)
        tracer3 = Tracer(allRays3, optics)
        pg.exec()

########################################################
########################################################        
if __name__ == "__main__":
    global Grating_ID
    GratingID = 3
    Groove = 300
    DK480_control = DK480_control_refactor.DK480Control("COM4", 9600)
    if DK480_control.connect():
        DK = DK480_control.DeviceOperation(DK480_control.ser)
        DK480_control.disconnect()
        pass
    app = QApplication(sys.argv)
    window = MainWindow(GratingID = 3)
    # subWindow = SubWindow()
    app.exec_()

# %%
