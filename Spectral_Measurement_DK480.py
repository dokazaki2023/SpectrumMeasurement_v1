#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 28 14:00:25 2022

@author: okazakidaiki
"""
#%%
from PyQt5.QtWidgets import QButtonGroup,QFileDialog,QMainWindow,QApplication,QWidget
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, Qt, QThreadPool, pyqtSlot
from PyQt5 import uic
import sys
import DK480_control
import numpy as np
import pyqtgraph as pg
import uuid
import datetime
import os
from pyqtgraph import Point
from optics import *
import pyqtgraph.exporters # pg.exporters を呼ぶために必要

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        global dlg1,dlg2,times
        times = 0
        dlg1 = uic.loadUi("DK480.ui")  # 作成した page1.ui を読み出して, ダイアログ1を作成
        dlg2 = uic.loadUi("DK480_Raytrace.ui")
        self.threadpool = QThreadPool()
        self.x = {}
        self.y = {}
        self.lines = {}
        self.lines2 = {}

        ## Default ##
        dlg1.LineEdit_Folders.setText("C:\\Users\\okazaki\\Desktop\\実験データ\\")
        dlg1.LineEdit_Data_Number.setText('0')
        dlg1.LineEdit_Entrance.setText('100')
        dlg1.LineEdit_Resolution_Wavenumber.setText('0.50')
        dlg1.LineEdit_Resolution_Frequency.setText('15')
        dlg1.LineEdit_Resolution_Wavelength.setText('0.26')
        dlg1.LineEdit_Target_WL.setText('4500')
        dlg1.LineEdit_Start_WL.setText('4500')
        dlg1.LineEdit_Stop_WL.setText('5000')
        dlg1.LineEdit_Target_WN.setText('4444.44')
        dlg1.LineEdit_Start_WN.setText('5000')
        dlg1.LineEdit_Stop_WN.setText('4000')
        dlg1.LineEdit_Step_WL.setText('4')
        dlg1.LineEdit_Sampling_Rate.setText('Not Ready')
        dlg1.LineEdit_Sampling_Number.setText('Not Ready')
        
        ## Toggle Button ##
        dlg1.radioButton1.toggled.connect(lambda:self.btnstate(dlg1.radioButton1))
        dlg1.radioButton2.toggled.connect(lambda:self.btnstate(dlg1.radioButton2))
        dlg1.radioButton3.toggled.connect(lambda:self.btnstate(dlg1.radioButton3))
        btngroup_Grating = QButtonGroup()
        btngroup_Grating.addButton(dlg1.radioButton1,1)
        btngroup_Grating.addButton(dlg1.radioButton2,1)
        btngroup_Grating.addButton(dlg1.radioButton3,1)
        
        ## Combo ##
        dlg1.ComboBox_DR.activated[str].connect(self.DynamicReserve)
        dlg1.ComboBox_IntegrationTime.activated[str].connect(self.Integration)
        dlg1.ComboBox_Sensitivity.activated[str].connect(self.Sensitivity)
        
        ## Check Box ##
        dlg1.CheckBox_LockIn.stateChanged.connect(lambda: self.LockIn(dlg1.CheckBox_LockIn.checkState()))
        
        ## Push Button ##
        dlg1.Button_Close.clicked.connect(self.close_application)
        dlg2.Button_Close.clicked.connect(self.close_application2)
        dlg1.Button_Folder.clicked.connect(self.Folder)
        dlg1.Button_Change_Slit.clicked.connect(self.ChangeSlit)
        dlg1.Button_Go.clicked.connect(self.Go)
        dlg1.Button_Measure.clicked.connect(self.execute)
        dlg1.Button_Update.clicked.connect(self.Update)

        font = 'Yu Gothic UI'
        p1 = dlg1.graphicsView1.plotItem
        p1.setLabel('bottom', '<font face="' + font + '">' + 'Wavelength (nm)</font>')
        p1.setLabel('left', '<font face="' + font + '">' + 'Power spectrum (a.u.)</font>')
        p1.getAxis('bottom').setPen(pg.mkPen(color='w', width=1.0))
        p1.getAxis('left').setPen(pg.mkPen(color='w', width=1.0))
        font_obj = QtGui.QFont()
        font_obj.setFamily(font)
        p1.getAxis("left").tickFont = font_obj
        p1.getAxis("bottom").tickFont = font_obj
        
        p2 = dlg1.graphicsView2.plotItem
        p2.setLabel('bottom', '<font face="' + font + '">' + 'Wavelength (nm)</font>')
        p2.setLabel('left', '<font face="' + font + '">' + 'Power spectrum (a.u.)</font>')
        p2.getAxis('bottom').setPen(pg.mkPen(color='w', width=1.0))
        p2.getAxis('left').setPen(pg.mkPen(color='w', width=1.0))
        p2.getAxis("left").tickFont = font_obj
        p2.getAxis("bottom").tickFont = font_obj
        p2.setLogMode(False, True)
        dlg1.show()
        
    def Update(self):
        global WL_Target, WL_Start, WL_Stop 
        c = 2.997924*10**(8)
        Slit = float(dlg1.LineEdit_Entrance.text())
        WL_Target = float(dlg1.LineEdit_Target_WL.text())
        WL_Start = float(dlg1.LineEdit_Start_WL.text())
        WL_Stop = float(dlg1.LineEdit_Stop_WL.text())
        
        try:
            WN_Target = np.round(1/(WL_Target*1e-7),2)
            WN_Start = np.round(1/(WL_Start*1e-7),2)
            WN_Stop = np.round(1/(WL_Stop*1e-7),2)
        except:
            return
        dlg1.LineEdit_Target_WN.setText(str(WN_Target))
        dlg1.LineEdit_Start_WN.setText(str(WN_Start))
        dlg1.LineEdit_Stop_WN.setText(str(WN_Stop))
        
        try:
            Resolution_Slit = WL_Target * Slit / 1e6
            Resolution_Grating =  WL_Target /(Groove*60)
            Resolution_WL = np.sqrt(Resolution_Slit**2 + Resolution_Grating**2)
            Resolution_Frequency = (c*(Resolution_WL*1e-9)/((WL_Target*1e-9)**2))
            Resolution_WN = Resolution_Frequency / (c*1e2)
            Resolution_WL = np.round(Resolution_WL,3)
            Resolution_Frequency = np.round(Resolution_Frequency*1e-9,3)
            Resolution_WN = np.round(Resolution_WN,3)
        except:
            return
        dlg1.LineEdit_Resolution_Wavelength.setText(str(Resolution_WL))
        dlg1.LineEdit_Resolution_Wavenumber.setText(str(Resolution_WN))
        dlg1.LineEdit_Resolution_Frequency.setText(str(Resolution_Frequency))
        dlg1.textEdit.show()

    def Trace(self):
        subWindow = SubWindow()
        
    def keyPressEvent(self,e): # エスケープキーを押すと画面が閉じる
        if e.key() == Qt.Key_Escape:
            print('Turned off')
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The Application is closed')
            dlg1.close()
    
    def close_application(self):
        print('Turned off')
        dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The Application is closed')
        dlg1.close()    
            
    def close_application2(self):
        dlg2.close()  
        
    def Folder(self):
        global file_path
        file_path = QFileDialog.getExistingDirectory()
        if len(file_path) == 0:
            return
        file_path = file_path.replace('/', chr(92))+chr(92)
        dlg1.textEdit.append('Path: ' + file_path) # 文字を表示する
        dlg1.LineEdit_Folders.setText(str(file_path))
    
    def btnstate(self,b):
        global GratingID, Groove
        DK.PreCheck()  
        if b.text() == "1200 L/mm, 750 nm, 480-1500 nm":
            if  b.isChecked() == True:          
                GratingID = 1
                Groove = 1200
                print (b.text()+" is selected")
            else:
                print (b.text()+" is deselected")
        if b.text() == "600 L/mm, 1600 nm, 950-3000 nm":
            if  b.isChecked() == True:
                GratingID = 2
                Groove = 600
                print (b.text()+" is selected")
            else:
                print (b.text()+" is deselected")
        if b.text() == "300 L/mm, 3000 nm, 1800-6000 nm":
            if  b.isChecked() == True:
                GratingID = 3
                Groove = 300
                print (b.text()+" is selected")
            else:
                print (b.text()+" is deselected")
        DK.GratingSelect(GratingID)

        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >"
            redText += str(datetime.datetime.now()) + ' : Timeout occurs ! '
            redText += "</span>"
            dlg1.textEdit.append(redText)
        else:
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Grating is successfully changed to the Grating ' + str(GratingID)) # 文字を表示する
            dlg1.textEdit.show()
            
        return GratingID, Groove

    def ChangeSlit(self):
        DK.PreCheck()
        SW_Entrance = float(dlg1.LineEdit_Entrance.text())
        DK.SlitAdjust(SW_Entrance)
        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >"
            redText += str(datetime.datetime.now()) + ' : Timeout occurs ! '
            redText += "</span>"
            dlg1.textEdit.append(redText)
        else:
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Entrance slit is set to ' + str(SW_Entrance) + ' um') # 文字を表示する
            dlg1.textEdit.show()
        
    def Go(self):
        global WL_Target
        DK.PreCheck()
        WL_Target = float(dlg1.LineEdit_Target_WL.text())
        DK.GoTo(WL_Target)
        if DK.flag_timeout:
            redText = "<span style=\" color:#ff0000;\" >"
            redText += str(datetime.datetime.now()) + ' : Timeout occurs ! '
            redText += "</span>"
            dlg1.textEdit.append(redText)
        else:
            print('Center wavelength is set to ' + str(np.round(WL_Target,2)) + ' nm')
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Center wavelength is set to ' + str(np.round(WL_Target,2)) + ' nm') # 文字を表示する
            dlg1.textEdit.show()
            

########################################################
########################################################
    def LockIn(self,state):
        global LIA1, inst_LI
        if state == Qt.Checked:
            import LI5640_control # visaの取
            inst_LI = LI5640_control.Connect('GPIB0::2::INSTR')
            LIA1 = LI5640_control.Lockin(inst_LI)
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Lock-In amplifier is connected') # 文字を表示する
            dlg1.textEdit.show() 
            print('Lock in measurement system is ready')
        
    def DynamicReserve(self,text): 
        if text == 'LOW':
            inst_LI.write("DRSV 2") # ダイナミックリザーブ 低 (noisy な時は高く)
        if text == 'MIDDLE':
            inst_LI.write("DRSV 1") 
        if text == 'HIGH':
            inst_LI.write("DRSV 0") 
        print('Dynamic Reserve : ' + text +' is selected')
        dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Dynamic Reserve : ' + text + ' is selected') # 文字を表示する
        dlg1.textEdit.show()  

    def Integration(self,text): 
        if text == '1 ms':
            inst_LI.write("TCON 4") # time constant
        if text == '3 ms':
            inst_LI.write("TCON 5")
        if text == '10 ms':
            inst_LI.write("TCON 6")
        if text == '30 ms':
            inst_LI.write("TCON 7")
        if text == '100 ms':
            inst_LI.write("TCON 8")
        if text == '300 ms':
            inst_LI.write("TCON 9")
        if text == '1000 ms':
            inst_LI.write("TCON 10")
        print('Time constant : ' + text +' is selected')
        dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Time constant : ' + text + ' is selected') # 文字を表示する
        dlg1.textEdit.show()  

    def Sensitivity(self,text): 
        if text == '1 V':
            inst_LI.write("VSEN 26")
        if text == '500 mV':
            inst_LI.write("VSEN 25")
        if text == '200 mV':
            inst_LI.write("VSEN 24")
        if text == '100 mV':
            inst_LI.write("VSEN 23")
        if text == '50 mV':
            inst_LI.write("VSEN 22")
        if text == '20 mV':
            inst_LI.write("VSEN 21")
        if text == '10 mV':
            inst_LI.write("VSEN 20")
        if text == '5 mV':
            inst_LI.write("VSEN 19")
        if text == '2 mV':
            inst_LI.write("VSEN 18")
        if text == '1 mV':
            inst_LI.write("VSEN 17")
        if text == '500 uV':
            inst_LI.write("VSEN 16")
        if text == '200 uV':
            inst_LI.write("VSEN 15")
        if text == '100 uV':
            inst_LI.write("VSEN 14")
        if text == '50 uV':
            inst_LI.write("VSEN 13")
        if text == '20 uV':
            inst_LI.write("VSEN 12")
        if text == '10 uV':
            inst_LI.write("VSEN 11")
        if text == '5 uV':
            inst_LI.write("VSEN 10")
        if text == '2 uV':
            inst_LI.write("VSEN 9")
        if text == '1 uV':
            inst_LI.write("VSEN 8")
        if text == '500 nV':
            inst_LI.write("VSEN 7")
        if text == '200 nV':
            inst_LI.write("VSEN 6")
        if text == '100 nV':
            inst_LI.write("VSEN 5")
        print('Sensitivity : ' + text +' is selected')
        dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Sensitivity : ' + text + ' is selected') # 文字を表示する
        dlg1.textEdit.show()       

########################################################
########################################################
    def BG(self):
        global BG
        BG_data = []
        for i in range (100):
            LIA1.Prepare_R()
            LIA1.Trigger()
            BG_now = LIA1.Get_R()
            BG_data.append(BG_now)
        BG = np.average(BG_data)
        dlg1.textEdit.append('BG measurement is finished')
    
    def execute(self):
        dlg1.graphicsView1.clear()
        dlg1.graphicsView2.clear()
        DK.PreCheck()
        worker = Worker()
        worker.signals.data.connect(self.receive_data)
        self.threadpool.start(worker) # Execute

    def receive_data(self, data):
        worker_id, x, y = data
        if worker_id not in self.lines:
            self.x[worker_id] = [x]
            self.y[worker_id] = [y]
            self.lines[worker_id] = dlg1.graphicsView1.plot(self.x[worker_id],self.y[worker_id])
            self.lines2[worker_id]= dlg1.graphicsView2.plot(self.x[worker_id],np.abs(self.y[worker_id]))
            return
        self.x[worker_id].append(x) # Update existing plot/data
        self.y[worker_id].append(y)
        self.lines[worker_id].setData(self.x[worker_id], self.y[worker_id])
        self.lines2[worker_id].setData(self.x[worker_id], np.abs(self.y[worker_id]))


class WorkerSignals(QObject):
    data = pyqtSignal(tuple)
    
class Worker(QRunnable):
    def __init__(self):
        super().__init__()
        self.worker_id = uuid.uuid4().hex  # Unique ID for this worker.
        self.signals = WorkerSignals()
        
    @pyqtSlot()
    def run(self):
        global Wavelength,Spectrum,times,WL
        
        BG = 0
        
        WL_Start = float(dlg1.LineEdit_Start_WL.text())
        WL_Stop = float(dlg1.LineEdit_Stop_WL.text())
        WL_step = float(dlg1.LineEdit_Step_WL.text())
        # Sampling_Number = float(dlg1.LineEdit_Sampling_Number.text())
        # Sampling_Rate = int(1e3*float(dlg1.LineEdit_Sampling_Rate.text()))     
        
        WL = WL_Start
        Wavelength = WL_Start
        Spectrum = 0
        LIA1.Prepare_R()
        LIA1.Trigger()
        while WL <= WL_Stop:
            DK.PreCheck()
            DK.GoTo(WL)
            data = LIA1.Get_R()
            Data_Mean = np.average(data[0])
            self.signals.data.emit((self.worker_id, WL, Data_Mean))  
            WL = WL + WL_step
            Wavelength = np.r_[WL, Wavelength]
            Spectrum = np.r_[Data_Mean, Spectrum]
            
        # ## save datas
        dammy = np.zeros(len(Wavelength))
        folder = str(dlg1.LineEdit_Folders.text())
        savedata = np.array([dammy.T,Wavelength,Spectrum])
        saves = savedata.transpose()
        folder = str(dlg1.LineEdit_Folders.text())
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
                    dlg1.LineEdit_Data_Number.setText(str(times))
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
            exporter = pg.exporters.ImageExporter(dlg1.graphicsView1.scene()) # exportersの直前に pg.QtGui.QApplication.processEvents() を呼ぶ！
            exporter.parameters()['width'] = 1000
            exporter.export(filename1)
            
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : Measurement No.'+str(int(dlg1.LineEdit_Data_Number.text()))+ ' is finished')
            times = int(dlg1.LineEdit_Data_Number.text()) + 1 # measurement number
            dlg1.LineEdit_Data_Number.setText(str(times))
            
            text = str(dlg1.textEdit.toPlainText())
            with open(filename2, 'w') as f:
                f.write(text)
            dlg1.textEdit.append(str(datetime.datetime.now()) + ' : The datas are saved successefully.') 
            print('ファイルは正常に保存されました。')
        except:
            print('ファイルの保存に失敗しました。')
            redText = "<span style=\" color:#ff0000;\" >"
            redText += str(datetime.datetime.now()) + ' : ERROR: Data saving failed '
            redText += "</span>"
            dlg1.textEdit.append(redText)
        dlg1.textEdit.show()

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
    inst_DK  = DK480_control.Connect()
    DK = DK480_control.DK480(inst_DK)
    app = QApplication(sys.argv)
    window = MainWindow()
    # subWindow = SubWindow()
    app.exec_()

# %%
