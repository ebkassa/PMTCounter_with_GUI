# -*- coding: utf-8 -*-
"""
Created on Thu Feb  9 16:22:56 2023

@author: Seigen
"""

import sys
import time
import XEM7305_photon_counter
import random
#import matplotlib
#matplotlib.use('Qt5Agg')

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, 
        QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, QSizePolicy,
        QSpinBox, QVBoxLayout, QWidget, QMainWindow)


from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg

# const
BYTES_PER_COUNT = 4
REDRAW_TIME = 60 # 80 # pipeOut I/O and plot animation time per frame. (80ms might be good for matplotlib cla and draw, 60 mus might be good for pyqtgraph)
DEBUG = True
SIMULATE = True
FIXED_PIPEOUT_LEN = 16
COUNT_BASELINE = 1000000 # simulated count value for 1 second period, assuming the input pulse in frequency of 1MHz.

class GraphPMT(PlotWidget):
    """
    The widget to draw PMT counter graph
    GraphPMT inherits MplCanvas, which inherits FigureCanvas. 
    So that itself is a canvas, just use its self.axes.plot and self.draw!
    """
    def __init__(self, *args, **kwargs):
        super(GraphPMT, self).__init__(*args, **kwargs)
        self.n_from_start = 0 # the number of the output from start monitering.
        self.compute_init_fig()
        
    def compute_init_fig(self, n_frame = 101, x_inc = 1):
        self.n_frame = n_frame
        self.x_inc = x_inc
        self.xdata = [(i+1-self.n_frame)*self.x_inc for i in range(self.n_frame)] #x: initial values: negtive to 0
        self.x_new = 1 * self.x_inc # x: the time of the new frame updated
        self.ydata = [0 for _ in range(self.n_frame)] # initial to 0s
        
        self.setBackground('w')
        self.pen = pg.mkPen('b', width=1)
        
        self.plot_ref = self.plot(self.xdata, self.ydata, pen=self.pen) 
        
    def start_update(self, dev=None, countingType=0, pipeOutLen = 128, updateInterval=100, lockincompen=1, lockinupr=1, lockindownr=1, n_frame=101, lockinupperiod=100, lockindownperiod=100, initwithfirstin=0):
        # if n_frame (number of points in a graph) changed. ydata shape must change with it. (xdata is intrinsically changed by re-calculate the range.)
        self.n_from_start = 0
        
        if (self.n_frame > n_frame):
            self.ydata = self.ydata[self.n_frame - n_frame : self.n_frame]
        elif (self.n_frame < n_frame):
            self.ydata = [0 for _ in range(n_frame - self.n_frame)] + self.ydata
        self.n_frame = n_frame
        
        self.plot_ref.clear() # self.plot_ref must exist to run .clear(). 
        self.x_inc = updateInterval * 1e-3
        self.xdata = [(i+1-self.n_frame)*self.x_inc for i in range(self.n_frame)] #x: initial values: negtive to 0
        self.plot_ref.setData(self.xdata, self.ydata)
        self.setXRange(self.xdata[0], self.xdata[self.n_frame-1], padding=0)
        self.debugIndex = 0 # control debug output number

        gtitle = ""
        gleftlbl = "Count per " + str(updateInterval) + " ms"
        gbottomlbl = "timeline/s"
        gstyles = {'color':'black', 'font-size':'16px'}
        
        if DEBUG:
            print("In start_update() ", dev, countingType, pipeOutLen, updateInterval, lockincompen, lockinupr, lockindownr, n_frame)
        if (dev is not None): 
            self.buff = [bytearray(BYTES_PER_COUNT * pipeOutLen) for _ in range(2)]
            if (countingType == 0): #f1: Normal diff
                dev.start_photon_count()
                gtitle = "Normal counting"
            elif (countingType == 1 or countingType == 2): #f2: lock-in. f3: lock-in diff.
                dev.start_lockin_count()
                gtitle = "Lock-in counting"
                if (countingType == 1):
                    gleftlbl = "Effective Count Accumulated"
                else:
                    gleftlbl = "Count gained per Lock-in period"
        
        self.setTitle(gtitle, **gstyles)
        self.setLabel('left', gleftlbl, **gstyles)
        self.getAxis('left').setPen('black')
        self.getAxis('left').setTextPen('black')
        self.setLabel('bottom', gbottomlbl, **gstyles)
        self.getAxis('bottom').setPen('black')
        self.getAxis('bottom').setTextPen('black')
        
        
        self.pre_value = 0
        self.timer = QTimer()
        interval = updateInterval - REDRAW_TIME # REDRAW_TIME is time needed for I/O and graph render. Set as a const.
        if (interval < 0): 
            interval = 0
        if (DEBUG == True):
            print("Timer interval", interval)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(lambda: self.update_plot(dev=dev, countingType=countingType, pipeOutLen=pipeOutLen, lockincompen=lockincompen, lockinupr=lockinupr, lockindownr=lockindownr, lockinupperiod= lockinupperiod, lockindownperiod= lockindownperiod, initwithfirstin=initwithfirstin))
        self.timer.start()

    def stop_update(self):
        if (self.timer is not None):
            self.timer.stop()
    
    def update_plot(self, dev=None, countingType=0, pipeOutLen=128, lockincompen=1, lockinupr=1, lockindownr=1,  lockinupperiod=100, lockindownperiod=100, initwithfirstin=0):
        self.n_from_start = self.n_from_start + 1
        # current real count value
        if (SIMULATE != True and dev is not None):
            dev.pipe_out(self.buff[1])
            cur_value = int.from_bytes(self.buff[1][(pipeOutLen-1)*BYTES_PER_COUNT : pipeOutLen*BYTES_PER_COUNT], "little") 
            
        # Simulation: replace current real count value with the simulated value. 
        elif (SIMULATE == True):
            time.sleep(self.x_inc) # simulate delay of pipe out
            if (countingType == 1 or countingType == 2):
                y_up = lockinupperiod / 1e3 * COUNT_BASELINE + random.randint(-1,1)
                y_down = lockindownperiod / 1e3 * COUNT_BASELINE + random.randint(-1,1)
                if (lockincompen == 1):
                    cur_value = self.pre_value + y_up * lockindownr - y_down * lockinupr # simulate count value for lock-in with compensation
                else:
                    cur_value = self.pre_value + y_up - y_down # simulate count value for lock-in without compensation
            else:
                cur_value = self.pre_value + self.x_inc * COUNT_BASELINE + random.randint(-5,5) # simulate count value for normal counting
                
        # Processing the count values to plot the graph. Apply to either current real count value or the simulated value.
        if (countingType == 0): #f1: Normal diff.
            if (self.pre_value > 4e9 and cur_value < 2e8): #overflow
                self.pre_value = self.pre_value - 4294967296 # When cur_value overflow, only processing pre_value (because we only care the diff between cur_value and pre_value). Otherwise, the subsequent values need overflow processing too.
            y_new = cur_value - self.pre_value
        if (countingType == 1 or countingType == 2): #f2: lock-in. or #f3: lock-in diff.
            if (cur_value > 4200000000): #underflow
                cur_value = cur_value - 4294967296
            if (lockincompen == 1):
                if (DEBUG == True and self.debugIndex < 3):
                    print(cur_value)
                cur_value = cur_value / lockindownr # normalize
                if (DEBUG == True and self.debugIndex < 3):
                    print(cur_value)
                    self.debugIndex = self.debugIndex + 1
            if (countingType == 1): #f2: lock-in
                y_new = cur_value
            else:  #f3: lock-in diff.
                y_new = cur_value - self.pre_value
        
        self.pre_value = cur_value # update previous value, prepare to get next output.
                
        self.ydata = self.ydata[1:] + [y_new]
        if (self.n_from_start == 1 and initwithfirstin == 1):
            self.ydata = [y_new for _ in range(self.n_frame)]
        self.xdata = self.xdata[1:] + [self.x_new]
        self.x_new = self.x_new + self.x_inc
        self.setXRange(self.xdata[0], self.xdata[self.n_frame-1], padding=0)
        self.plot_ref.setData(self.xdata, self.ydata)
        
class MainWindow(QMainWindow):
    """ The main window of the GUI. Get the settings and start counting from this GUI. """
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.getDev()
        self.createSettingGroupBox()
        self.calcConfig()
        self.createGraphGroupBox()
        
        layout = QGridLayout()
        layout.addWidget(self._graphGroupBox, 0, 0)
        layout.addWidget(self._settingGroupBox, 0, 1)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 0)
        layout.setRowStretch(0, 1)
        
        #self.setLayout(layout) # It is good for QDialog, not for QMainWindow. It complains: QWidget::setLayout: Attempting to set QLayout "" on MainWindow "", which already has a layout. Instead, using widget to get the layout, and set the widget to the central widget.
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.setWindowTitle("PMT Counter")
        self.selectTTL()

    def getDev(self):
        if (SIMULATE != True):
            self.dev = XEM7305_photon_counter.XEM7305_photon_counter(bit_file='photon_counter_gui.bit')
        
    def delDev(self):
        if (SIMULATE != True):
            del self.dev._device
            del self.dev
        
    def restartDev(self):
        if (SIMULATE != True):
            self.delDev()
            self.getDev()
            self.selectTTL()

    def getSettings(self):
        """ get the settings from GUI """
        pass # moved to calcConfig(self)
        
    def calcConfig(self):
        """ get the settings from GUI, and calculate dependent settings  """
        try:
            lup = float(self.leLockinUpPeriod.text()) # the input might be not a numeric string
        except ValueError:
            lup = 0
        self.settingLockUpPeriod = lup
        self.settingLockUpRate = self.sbxLockinUp.value()
        self.settingLockDownRate = self.sbxLockinDown.value()
        if self.ckbLockinUpDownCompensate.isChecked() == True:
            self.settingCompensateLockinRatio = 1
        else:
            self.settingCompensateLockinRatio = 0
        
        self.settingGUpdateToLockinRate = self.sbxGUpdateToLockinRate.value()
        self.settingCountingType = self.cbbCountType.currentIndex()
        
        self.confLockDownPeriod = self.settingLockUpPeriod * self.settingLockDownRate / self.settingLockUpRate
        self.confLockPeriod = self.settingLockUpPeriod + self.confLockDownPeriod
        self.leLockinDownPeriod.setText(str(self.confLockDownPeriod))
        self.leLockinPeriod.setText(str(self.confLockPeriod))
        self.confGraphUpdateInterval = self.confLockPeriod * self.settingGUpdateToLockinRate
        self.leGUpdateInterval.setText(str(self.confGraphUpdateInterval))
        self.confPpoLen = FIXED_PIPEOUT_LEN
        self.confCountPeriod = self.confGraphUpdateInterval / self.confPpoLen
        
        try:
            gnp = int(self.leGNumPoint.text()) # the input might be not a numeric string
        except ValueError:
            gnp = 101
        self.n_frame = gnp
        self.leGNumPoint.setText(str(gnp))
        
        if self.ckbGInitWithFirstInput.isChecked():
            self.settingGInitWithFirstInput = 1 
        else:
            self.settingGInitWithFirstInput = 0
            
    def configFPGA(self):
        """ transform config values to FPGA device config """
        if (SIMULATE != True):
            self.dev.counting_period = self.confCountPeriod * 1e6 #from ms to ns
            self.dev.lockin_up_period = self.settingLockUpPeriod * 1e6
            self.dev.lockin_down_period = self.confLockDownPeriod * 1e6
            self.dev.lockin_up_rate = self.settingLockUpRate
            self.dev.lockin_down_rate = self.settingLockDownRate
            self.dev.lockin_updown_ratio_compensate = self.settingCompensateLockinRatio
            
    def debugInfo(self):
        print("DEBUG:", DEBUG)
        print("SIMULATE:", SIMULATE)
        print("Lock up period:", self.settingLockUpPeriod)
        print("Lock down period:", self.confLockDownPeriod)
        print("Lock period:", self.confLockPeriod)
        print("Pipe len in 1count:", self.confPpoLen)
        print("Counting period:", self.confCountPeriod)
        print("Graph update interval:", self.confGraphUpdateInterval)
        print("Lock up rate:", self.settingLockUpRate)
        print("Lock down rate:", self.settingLockDownRate)
        print("Lcok-in compensate: ", self.settingCompensateLockinRatio)
        if (SIMULATE != True and self.dev is not None):
            print("self.dev.counting_period:", self.dev.counting_period)
            print("self.dev.lockin_up_period:", self.dev.lockin_up_period)
            print("self.dev.lockin_down_period:", self.dev.lockin_down_period)
    
    def selectTTL(self):
        if (SIMULATE != True):
            self.settingTTLType = self.cbbTTLOutType.currentIndex()
            self.dev.output_TTL_type = self.settingTTLType
            self.dev.select_output_TTL()

    def start(self):
        """ Start fetching data from FPGA photon counter to draw the graph. """

        # re-initiate the device. without it, repeatedly using "Start" button in the GUI is not stable.
        self.restartDev() 

        #Fetch settings, and calculate all configurations needed 
        self.calcConfig() 
        
        #Config the FPGA device
        self.configFPGA()

        #Initiate FPGA counter, fetch its output to update the graph
        if (DEBUG == True) :
            self.debugInfo()
        if (SIMULATE == True) :
            mydev = None # simulation. self.dev is not available.
        else:
            mydev = self.dev
        self.graph1.start_update(dev=mydev, countingType=self.settingCountingType, pipeOutLen=self.confPpoLen, updateInterval=self.confGraphUpdateInterval, lockincompen=self.settingCompensateLockinRatio, lockinupr=self.settingLockUpRate, lockindownr=self.settingLockDownRate, n_frame=self.n_frame, lockinupperiod=self.settingLockUpPeriod, lockindownperiod=self.confLockDownPeriod, initwithfirstin=self.settingGInitWithFirstInput)  # Initiate the FPGA counter, infinite loop to pipeout counts to update the graph. (In simulation, dev is None, just infinite loop to get the simulated value.)
    
    def stop(self):
        self.graph1.stop_update()
        
    def createGraphGroupBox(self):
        """ Arrange two graphs into a group """
        self._graphGroupBox = QGroupBox("Graphs")
        self.graph1 = GraphPMT(n_frame = self.n_frame)
        
        #row2 = GraphPMT()
        group = QVBoxLayout()
        group.addWidget(self.graph1)
        #group.addWidget(row2)
        self._graphGroupBox.setLayout(group)
        
    def createSettingGroupBox(self):
        """ Arrange all the widgets for the settings into a group. """
        self._settingGroupBox = QGroupBox("Settings")
        
        rowLockinUpPeriod = QHBoxLayout()
        lblLockinUpPeriod = QLabel("Lock-in counting up period (ms)    ")
        self.leLockinUpPeriod = QLineEdit('50') #make the widget a member of the class MainWindow to be easy to access.
        self.leLockinUpPeriod.textEdited.connect(self.calcConfig)
        rowLockinUpPeriod.addWidget(lblLockinUpPeriod)
        rowLockinUpPeriod.addWidget(self.leLockinUpPeriod)
        
        rowLockinDownPeriod = QHBoxLayout()
        lblLockinDownPeriod = QLabel("Lock-in counting down period (ms)")
        self.leLockinDownPeriod = QLineEdit('')
        self.leLockinDownPeriod.setEnabled(False)
        rowLockinDownPeriod.addWidget(lblLockinDownPeriod)
        rowLockinDownPeriod.addWidget(self.leLockinDownPeriod)
        
        rowLockinPeriod = QHBoxLayout()
        lblLockinPeriod = QLabel("Lock-in period (ms)                ")
        self.leLockinPeriod = QLineEdit('')
        self.leLockinPeriod.setEnabled(False)
        rowLockinPeriod.addWidget(lblLockinPeriod)
        rowLockinPeriod.addWidget(self.leLockinPeriod)
        
        rowLockinUpDownRatio = QHBoxLayout()
        lblLockinUpDownRatio = QLabel("Lock-in up/down period ratio")
        self.sbxLockinUp = QSpinBox()
        self.sbxLockinUp.setValue(1)
        self.sbxLockinUp.setRange(1,99)
        self.sbxLockinUp.valueChanged.connect(self.calcConfig)
        lblSlash = QLabel("  /")
        self.sbxLockinDown = QSpinBox()
        self.sbxLockinDown.setValue(1)
        self.sbxLockinDown.setRange(1,99)
        self.sbxLockinDown.valueChanged.connect(self.calcConfig)
        rowLockinUpDownRatio.addWidget(lblLockinUpDownRatio)
        rowLockinUpDownRatio.addWidget(self.sbxLockinUp)
        rowLockinUpDownRatio.addWidget(lblSlash)
        rowLockinUpDownRatio.addWidget(self.sbxLockinDown)
        
        self.ckbLockinUpDownCompensate = QCheckBox("Compensate lock-in up/down period ratio")
        self.ckbLockinUpDownCompensate.setChecked(True)
        
        rowGUpdateInterval = QHBoxLayout()
        lblGUpdateInterval = QLabel("Graph (count value) update interval (ms)")
        self.leGUpdateInterval = QLineEdit('')
        self.leGUpdateInterval.setEnabled(False)
        rowGUpdateInterval.addWidget(lblGUpdateInterval)
        rowGUpdateInterval.addWidget(self.leGUpdateInterval)
        
        rowGUpdateToLockinRate = QHBoxLayout()
        lblGUpdateToLockinRate = QLabel("Graph update interval: x times of Lock-in period ")
        self.sbxGUpdateToLockinRate = QSpinBox()
        self.sbxGUpdateToLockinRate.setValue(1)
        self.sbxGUpdateToLockinRate.setRange(1,10)
        self.sbxGUpdateToLockinRate.valueChanged.connect(self.calcConfig)
        rowGUpdateToLockinRate.addWidget(lblGUpdateToLockinRate)
        rowGUpdateToLockinRate.addWidget(self.sbxGUpdateToLockinRate)

        
        rowCountType = QHBoxLayout()
        lblCountType = QLabel("Counting type:")
        self.cbbCountType = QComboBox()
        self.cbbCountType.addItems(["f1: Normal diff", "f2: Lock-in", "f3: Lock-in diff"])
        rowCountType.addWidget(lblCountType)
        rowCountType.addWidget(self.cbbCountType)
        
        group = QVBoxLayout()
        group.addLayout(rowLockinUpPeriod)
        group.addSpacing(6)
        group.addLayout(rowLockinDownPeriod)
        group.addSpacing(6)
        group.addLayout(rowLockinPeriod)
        group.addSpacing(6)
        group.addLayout(rowLockinUpDownRatio)
        group.addSpacing(16)
        group.addWidget(self.ckbLockinUpDownCompensate)
        group.addSpacing(16) 
        group.addLayout(rowGUpdateInterval)
        group.addSpacing(6)
        group.addLayout(rowGUpdateToLockinRate)
        group.addSpacing(16)
        group.addLayout(rowCountType)
        
        rowGNumPoint = QHBoxLayout()
        lblGNumPoint = QLabel("Number of points in a graph ")
        self.leGNumPoint = QLineEdit('500')
        rowGNumPoint.addWidget(lblGNumPoint)
        rowGNumPoint.addWidget(self.leGNumPoint)
        
        group.addSpacing(16)
        group.addLayout(rowGNumPoint)
        
        self.ckbGInitWithFirstInput = QCheckBox("Using first value to initiate previous (blank) points ")
        self.ckbGInitWithFirstInput.setChecked(True)
        
        group.addSpacing(6)
        group.addWidget(self.ckbGInitWithFirstInput)
        
        self.btnStart = QPushButton("Start Monitoring")
        self.btnStart.clicked.connect(self.start)
        group.addSpacing(6) # group.addSpacing(30) #
        group.addWidget(self.btnStart)
        
        self.btnStop = QPushButton("Stop Monitoring")
        self.btnStop.clicked.connect(self.stop)
        group.addSpacing(6) # group.addSpacing(30) #
        group.addWidget(self.btnStop)
        
        rowTTLOutType = QHBoxLayout()
        lblTTLOutType = QLabel("Output TTL type:")
        self.cbbTTLOutType = QComboBox()
        self.cbbTTLOutType.addItems(["Always high", "Sync'd lock-in", "Alway low"])
        self.cbbTTLOutType.setCurrentIndex(1) # default: sync'd.
        rowTTLOutType.addWidget(lblTTLOutType)
        rowTTLOutType.addWidget(self.cbbTTLOutType)
        
        group.addStretch(1)
        group.addSpacing(16)
        group.addLayout(rowTTLOutType)
        
        self.btnSelectTTL = QPushButton("Select output TTL")
        self.btnSelectTTL.clicked.connect(self.selectTTL)
        group.addSpacing(6) # group.addSpacing(30) #
        group.addWidget(self.btnSelectTTL)
        
      
        
        
        self._settingGroupBox.setLayout(group)

# A sample of the usage of this class.
if __name__ == '__main__':
    if 'DEBUG' in sys.argv:
        DEBUG = True
    else:
        DEBUG = False
    if 'SIMU' in sys.argv:
        SIMULATE = True
    else:
        SIMULATE = False

    
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
