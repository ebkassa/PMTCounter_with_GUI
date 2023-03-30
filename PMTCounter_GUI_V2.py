# -*- coding: utf-8 -*-
"""
PMT Counter with GUI, version 2.
It gets and plots normal counting value and lock-in counting value at the same time.
Not compatible to version 1.

@author: Seigen Nakasone
"""

import sys
import time
import XEM7305_photon_counter_V2
import random

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, 
        QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QPushButton, 
        QSpinBox, QVBoxLayout, QWidget, QMainWindow)


from pyqtgraph import PlotWidget
import pyqtgraph as pg

# const
BYTES_PER_COUNT = 4
REDRAW_TIME = 50 # 80 # pipeOut I/O and plot animation time per frame. (80ms might be good for matplotlib cla and draw, 60 mus might be good for pyqtgraph)
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
        self.init_dammy_plot()
        
    def init_dammy_plot(self, n_frame = 101, x_inc = 1):
        """ Draw a dumy graph with dumy parameters """
        self.n_frame = n_frame
        self.x_inc = x_inc
        self.xdata = [float((i+1-self.n_frame)*self.x_inc) for i in range(self.n_frame)] #initial x from negtive to 0
        self.x_new = 1 * self.x_inc # the new x value when frame updated
        self.ydata = [0.0 for _ in range(self.n_frame)] # initial to 0s
        
        self.setBackground('w')
        self.pen = pg.mkPen('b', width=1)
        
        self.plot_ref = self.plot(self.xdata, self.ydata, pen=self.pen) 
        
    def init_plot(self, countingType=0, updateInterval=100, n_frame=101):
        """ Using the real parameters to initiate the graph. Unit of updateInterval: ms."""
        self.plot_ref.clear() # self.plot_ref must exist to run .clear(). 
        
        self.n_from_start = 0
        self.countingType = countingType
        
        # if n_frame (number of points in a graph) changed. ydata shape must change with it. (xdata is automatically changed by re-calculate the range.)
        # self.ydata = [0.0 for _ in range(n_frame)]
        if (self.n_frame > n_frame):
            self.ydata = self.ydata[self.n_frame - n_frame : self.n_frame]
        elif (self.n_frame < n_frame):
            self.ydata = [self.ydata[0] for _ in range(n_frame - self.n_frame)] + self.ydata

        self.n_frame = n_frame
         
        self.x_inc = updateInterval * 1e-3  # ms to s
        self.xdata = [float((i+1-self.n_frame)*self.x_inc) for i in range(self.n_frame)] #initial x from negtive to 0
        self.x_new = 1 * self.x_inc # the new x value when the frame is updated
        self.plot_ref.setData(self.xdata, self.ydata)
        self.setXRange(self.xdata[0], self.xdata[self.n_frame-1], padding=0)
        self.debugIndex = 0 # to control debug output number

        gtitle = ""
        gleftlbl = "Count per " + str(updateInterval) + " ms"
        gbottomlbl = "timeline/s"
        gstyles = {'color':'black', 'font-size':'16px'}
        
        if DEBUG:
            print("In start_update() ", countingType, updateInterval, n_frame)

        if (countingType == 0): #f1: Normal diff
            gtitle = "Normal counting"
        elif (countingType == 1 or countingType == 2): #f2: lock-in. f3: lock-in diff.
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
    
    def update_plot(self, cur_value_lck=0.0, cur_value=0.0, pre_value_lck=0.0, pre_value=0.0, initwithfirstin=0.0):
        """ Update the graph using new values """
        self.n_from_start = self.n_from_start + 1

        # Update y values for plot
        if (self.countingType == 0): #f1: normal
            y_new = float(cur_value - pre_value)
        elif (self.countingType == 1): #f2: lock-in
            y_new = float(cur_value_lck)
        else:  #f3: lock-in diff.
            y_new = float(cur_value_lck - pre_value_lck)
        
        self.ydata = self.ydata[1:] + [y_new]
        
        # Initiate y values with the first 3 counting values (using 3 because it is not stable just using the first 1 value).
        # It is a skill to force the plot to auto-scale to show the details of the counting value changes just after start_counting(). Otherwise, the details might only be shown after n_frame updates because y axis is scaled from 0 to a large value.
        if (self.n_from_start <= 3 and initwithfirstin == 1): 
            self.ydata = [y_new for _ in range(self.n_frame)] 
        
        self.xdata = self.xdata[1:] + [self.x_new]
        self.x_new = self.x_new + self.x_inc # the new x value when frame updated
        self.setXRange(self.xdata[0], self.xdata[self.n_frame-1], padding=0)
        self.plot_ref.setData(self.xdata, self.ydata)
        
class PMTCounter():
    """ 
    The PMT counter. Pipe out counting values from FPGA board, 
    and draw the 2 graphs for normal counting and lock-in counting. 
    """
    def __init__(self, *args, **kwargs):
        self.timer = None
        self.init_counts(self, *args, **kwargs)
        self.init_dummy_plots(self, *args, **kwargs)
        
    def init_counts(self, *args, **kwargs):
        self.cur_value_lck = 0
        self.cur_value = 0
        self.pre_value_lck = 0
        self.pre_value = 0
    
    def init_dummy_plots(self, *args, **kwargs):
        """ initiate plots with dummy parameters """
        self.graph0 = GraphPMT()
        self.graph1 = GraphPMT()
        self.graph0.setMinimumSize(800,200)
        self.graph1.setMinimumSize(800,200)
    
    def start_counting(self, dev=None, pipeOutLen=FIXED_PIPEOUT_LEN, updateInterval=100, lockincompen=1, lockinupr=1, lockindownr=1, lockinupperiod=50, lockindownperiod=50, g0type=0, g1type=1, n_frame=101, initwithfirstin=0):
        """ 
        It initiates the plots with real parameters, 
        and start the counter by initiate a timer to get new counting values periodically. 
        The unit of time periods (updateInterval, lockinupperiod, lockindownperiod): ms.
        """
        # initiate plots with real parameters
        self.graph0.init_plot(countingType=g0type, updateInterval=updateInterval, n_frame=n_frame)
        self.graph1.init_plot(countingType=g1type, updateInterval=updateInterval, n_frame=n_frame)

        # prepare to pipeout counts from FPGA
        self.x_inc = updateInterval * 1e-3  # ms to s
        if (dev is not None): 
            self.buff = [bytearray(BYTES_PER_COUNT * pipeOutLen) for _ in range(2)]
            dev.start_lockin_count() # now lock-in counting output both normal counts and lock-in counts.

        # Using a timer to pipeout counts from FPGA
        # Both real counter and the simulated counter will use this timer
        if (self.timer is not None):
            self.timer.stop()
            del self.timer
        self.timer = QTimer()
        
        self.interval = updateInterval - REDRAW_TIME # REDRAW_TIME is time needed for I/O and graph render. Set as a const.
        if (self.interval < 0): 
            self.interval = 0
        if (DEBUG == True):
            print("Timer interval", self.interval)
        self.timer.setInterval(int(self.interval))
        self.timer.timeout.connect(lambda: self.update_counts(dev=dev, pipeOutLen=pipeOutLen, lockincompen=lockincompen, lockinupr=lockinupr, lockindownr=lockindownr, lockinupperiod= lockinupperiod, lockindownperiod= lockindownperiod, initwithfirstin=initwithfirstin))
        self.timer.start()
        
    def stop_update(self):
        if (self.timer is not None):
            self.timer.stop()

    def update_counts(self, dev=None, pipeOutLen=FIXED_PIPEOUT_LEN, lockincompen=1, lockinupr=1, lockindownr=1,  lockinupperiod=50, lockindownperiod=50, initwithfirstin=0):
        """ 
        It pipes out the counting values from the FPGA device, and uses the new counting values to update the plots. 
        It is fired periodically by the timeout event of the timer.
        The unit of time periods (updateInterval, lockinupperiod, lockindownperiod): ms.
        """
        # Preserve the previous counting values
        self.pre_value = self.cur_value
        self.pre_value_lck = self.cur_value_lck
        
        # Count values. Now pipeout in format [{normal_count, lockin_count} * (FIXED_PIPEOUT_LEN/2)]
        if (SIMULATE != True and dev is not None):
            dev.pipe_out(self.buff[1])
            self.cur_value_lck = int.from_bytes(self.buff[1][(pipeOutLen-1)*BYTES_PER_COUNT : pipeOutLen*BYTES_PER_COUNT], "little")  # lock-in counts
            self.cur_value = int.from_bytes(self.buff[1][(pipeOutLen-2)*BYTES_PER_COUNT : (pipeOutLen-1)*BYTES_PER_COUNT], "little")  # normal counts
        # Simulation: replace current real count value with the simulated value. 
        elif (SIMULATE == True):
            simu_delay = self.x_inc - self.interval * 1e-3  # ms to s.
            if (simu_delay < 0.001): simu_delay = 0.001
            time.sleep(simu_delay) # to simulate the delay of the pipe out
            y_up = lockinupperiod / 1e3 * COUNT_BASELINE + random.randint(-1,1)
            y_down = lockindownperiod / 1e3 * COUNT_BASELINE + random.randint(-1,1)
            if (lockincompen == 1):
                self.cur_value_lck = self.pre_value_lck + y_up * lockindownr - y_down * lockinupr # simulate the counting value for lock-in with compensation
            else:
                self.cur_value_lck = self.pre_value_lck + y_up - y_down # simulate the counting value for lock-in without compensation
            self.cur_value = self.pre_value + self.x_inc * COUNT_BASELINE + random.randint(-5,5) # simulate the counting value for normal counting

        # Processing the count values to plot the graph. Apply to either current real count value or the simulated value.
        # Overflow and underflow processing
        if (self.pre_value > 4e9 and self.cur_value < 2e8): #overflow
            self.pre_value = self.pre_value - 4294967296 # When cur_value overflow, only processing pre_value (because we only care the diff between cur_value and pre_value). Otherwise, the subsequent values need overflow processing too.
        if (self.cur_value_lck > 4200000000): #underflow
            self.cur_value_lck = self.cur_value_lck - 4294967296
            
        # dubug rate compensation
        if (DEBUG == True):
            if (lockincompen == 1):
                if (self.debugIndex < 3):
                    print(self.cur_value_lck)
                self.cur_value_lck = self.cur_value_lck / lockindownr # normalize
                if (self.debugIndex < 3):
                    print(self.cur_value_lck)
                    self.debugIndex = self.debugIndex + 1
        
        # update plots with new count values
        self.graph0.update_plot(cur_value_lck = self.cur_value_lck, cur_value = self.cur_value, pre_value_lck = self.pre_value_lck, pre_value = self.pre_value, initwithfirstin = initwithfirstin)
        self.graph1.update_plot(cur_value_lck = self.cur_value_lck, cur_value = self.cur_value, pre_value_lck = self.pre_value_lck, pre_value = self.pre_value, initwithfirstin = initwithfirstin)
        
class MainWindow(QMainWindow):
    """ The main window of the GUI. Get the settings and start counting from this GUI. """
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        self.getDev()
        self.getCounter()
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
            self.dev = XEM7305_photon_counter_V2.XEM7305_photon_counter(bit_file='photon_counter_V2.bit')
        
    def delDev(self):
        if (SIMULATE != True):
            del self.dev._device
            del self.dev

    def clrDev(self):
        if (SIMULATE != True):
            self.dev.clear_dev()

    def reGetDev(self):
        if (SIMULATE != True):
            self.delDev()
            self.getDev()
            self.selectTTL()
    
    def getCounter(self):
        self.counter = PMTCounter()

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
        self.settingCountingType0 = self.cbbCountType0.currentIndex()
        self.settingCountingType1 = self.cbbCountType1.currentIndex()
        
        self.confLockDownPeriod = self.settingLockUpPeriod * self.settingLockDownRate / self.settingLockUpRate
        self.confLockPeriod = self.settingLockUpPeriod + self.confLockDownPeriod
        self.leLockinDownPeriod.setText(str(self.confLockDownPeriod))
        self.leLockinPeriod.setText(str(self.confLockPeriod))
        self.confGraphUpdateInterval = self.confLockPeriod * self.settingGUpdateToLockinRate
        self.leGUpdateInterval.setText(str(self.confGraphUpdateInterval))
        self.confPpoLen = FIXED_PIPEOUT_LEN 
        # self.confCountPeriod = self.confGraphUpdateInterval / self.confPpoLen #It was pipeout in format {count}, a flag dicide it is a normal or lockin count.
        self.confCountPeriod = self.confGraphUpdateInterval * 2 / self.confPpoLen  #now pipeout in format [{normal_count, lockin_count} * (FIXED_PIPEOUT_LEN/2)], that means each count period, 2 values (one normal count, one lock-in count) will be piped out.
        
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
            
    def configDev(self):
        """ transform config values to the device """
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
        #self.reGetDev() 
        self.clrDev()

        #Fetch settings, and calculate all configurations needed 
        self.calcConfig() 
        
        #Config the FPGA device
        self.configDev()


        if (DEBUG == True) :
            self.debugInfo()
            
        if (SIMULATE == True) :
            mydev = None
        else:
            mydev = self.dev
        #Initiate FPGA counter, fetch its output to update the graph
        self.counter.start_counting(dev=mydev, g0type=self.settingCountingType0, g1type=self.settingCountingType1, pipeOutLen=self.confPpoLen, updateInterval=self.confGraphUpdateInterval, lockincompen=self.settingCompensateLockinRatio, lockinupr=self.settingLockUpRate, lockindownr=self.settingLockDownRate, n_frame=self.n_frame, lockinupperiod=self.settingLockUpPeriod, lockindownperiod=self.confLockDownPeriod, initwithfirstin=self.settingGInitWithFirstInput)  # Initiate the FPGA counter, infinite loop to pipeout counts to update the graph. (In simulation, dev is None, just infinite loop to get the simulated value.)
    
    def stop(self):
        self.counter.stop_update()
        
    def createGraphGroupBox(self):
        """ Arrange two graphs into a group """
        self._graphGroupBox = QGroupBox("Graphs")
        group = QVBoxLayout()
        group.addWidget(self.counter.graph0)
        group.addWidget(self.counter.graph1)
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
        lblGUpdateToLockinRate = QLabel("Extend graph update interval to Lock-in period multiplied by:")
        self.sbxGUpdateToLockinRate = QSpinBox()
        self.sbxGUpdateToLockinRate.setValue(1)
        self.sbxGUpdateToLockinRate.setRange(1,10)
        self.sbxGUpdateToLockinRate.valueChanged.connect(self.calcConfig)
        rowGUpdateToLockinRate.addWidget(lblGUpdateToLockinRate)
        rowGUpdateToLockinRate.addWidget(self.sbxGUpdateToLockinRate)

        rowCountType0 = QHBoxLayout()
        lblCountType0 = QLabel("Graph1 Counting type:")
        self.cbbCountType0 = QComboBox()
        self.cbbCountType0.addItems(["f1: Normal diff", "f2: Lock-in", "f3: Lock-in diff"])
        rowCountType0.addWidget(lblCountType0)
        rowCountType0.addWidget(self.cbbCountType0)
        
        rowCountType1 = QHBoxLayout()
        lblCountType1 = QLabel("Graph2 Counting type:")
        self.cbbCountType1 = QComboBox()
        self.cbbCountType1.addItems(["f1: Normal diff", "f2: Lock-in", "f3: Lock-in diff"])
        self.cbbCountType1.setCurrentIndex(1) # graph2 default type: Lock-in
        rowCountType1.addWidget(lblCountType1)
        rowCountType1.addWidget(self.cbbCountType1)
        
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
        
        group.addStretch(1)
        group.addSpacing(16)
        group.addLayout(rowCountType0)
        group.addSpacing(16)
        group.addLayout(rowCountType1)
        
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
