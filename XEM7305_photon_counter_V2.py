"""
Module XEM7305_photon_counter_V2:
    This is the version 2 of XEM7305_photon_counter.
    In this version, normal counting and lock-in counting run and output at the same time.
    It is not compatible to version 1, which doesn't support 2 counts at the same time.

Usage: 
  Unit of time period: ns.
"""

import ok
import time
import sys
import ctypes
import numpy as np

class XEM7305_photon_counter:
    def __init__(self, dev_serial='', bit_file='photon_counter_V2.bit', counting_period=1e8/8, lockin_up_period=5e7, lockin_down_period = 5e7, clock_period=2.173913, lockin_up_rate = 1, lockin_down_rate = 1, lockin_updown_ratio_compensate = 1, output_TTL_type = 1):  #Unit of periods: ns.
        self._dev_serial = dev_serial # device serial of our FPGA is '2104000VK5'. Open the first FPGA if given a empty serial number ''. Get serial by _device.GetDeviceListSerial(0). 0 ~ the first device.
        self._bit_file = bit_file
        self._counting_period = counting_period
        self._lockin_up_period = lockin_up_period
        self._lockin_down_period = lockin_down_period
        self._clock_period = clock_period
        self._lock_in = 0 # 1: lock-in
        self._lockin_up_rate = lockin_up_rate
        self._lockin_down_rate = lockin_down_rate
        self._lockin_updown_ratio_compensate = lockin_updown_ratio_compensate # 1:compensate
        self._output_TTL_type = output_TTL_type # 0: High.  1: Sync'd.  2: Low
        self.init_dev()

    @property
    def dev_serial(self):
        return self._dev_serial

    @dev_serial.setter
    def dev_serial(self, dev_seri):
        self._dev_serial = dev_seri

    @property
    def bit_file(self):
        return self._bit_file

    @bit_file.setter
    def bit_file(self, bit_f):
        self._bit_file = bit_f
        
    @property
    def counting_period(self):
        return self._counting_period

    @counting_period.setter
    def counting_period(self, cnt_period):
        self._counting_period = cnt_period
    
    @property
    def lockin_up_period(self):
        return self._lockin_up_period

    @lockin_up_period.setter
    def lockin_up_period(self, lockinup_period):
        self._lockin_up_period = lockinup_period
        
    @property
    def lockin_down_period(self):
        return self._lockin_down_period

    @lockin_down_period.setter
    def lockin_down_period(self, lockindown_period):
        self._lockin_down_period = lockindown_period
    
    @property
    def clock_period(self):
        return self._clock_period

    @clock_period.setter
    def clock_period(self, clk_period):
        self._clock_period = clk_period

    @property
    def lock_in(self):
        return self._lock_in

    @lock_in.setter
    def lock_in(self, lockin):
        self._lock_in = lockin
        
    @property
    def lockin_up_rate(self):
        return self._lockin_up_rate

    @lockin_up_rate.setter
    def lockin_up_rate(self, lockin_up_rate):
        self._lockin_up_rate = lockin_up_rate
        
    @property
    def lockin_down_rate(self):
        return self._lockin_down_rate

    @lockin_down_rate.setter
    def lockin_down_rate(self, lockin_down_rate):
        self._lockin_down_rate = lockin_down_rate
    
    @property
    def lockin_updown_ratio_compensate(self):
        return self._lockin_updown_ratio_compensate

    @lockin_updown_ratio_compensate.setter
    def lockin_updown_ratio_compensate(self, lockin_updown_ratio_compensate):
        self._lockin_updown_ratio_compensate = lockin_updown_ratio_compensate
        
    @property
    def output_TTL_type(self):
        return self._output_TTL_type

    @output_TTL_type.setter
    def output_TTL_type(self, output_TTL_type):
        self._output_TTL_type = output_TTL_type

    def init_dev(self):
        self._device = ok.okCFrontPanel()
        if (self._device.GetDeviceCount() < 1):
            sys.exit("Error: no Opal Kelly FPGA device.")
        try: 
            self._device.OpenBySerial(self.dev_serial)
            error = self._device.ConfigureFPGA(self.bit_file)
        except:
            sys.exit("Error: can't open Opal Kelly FPGA device by serial number %s" % self.dev_serial)
        if (error != 0):
            sys.exit("Error: can't program Opal Kelly FPGA device by file %s" % self.bit_file)
            
    def select_output_TTL(self):
        self._device.SetWireInValue(0x08, int(self.output_TTL_type))
        self._device.UpdateWireIns()
        self._device.SetWireInValue(0x00, 0x04) # m_rst = 1, to reset MUX
        self._device.UpdateWireIns()
        self._device.SetWireInValue(0x00, 0x00) # de-assertion reset signal
        self._device.UpdateWireIns()
        
    def reset_dev(self):
        """ 
        Set reset signals of fifo and counting circuits to 1s, to reset those circuits,
        then, de-assert the reset signals to 0s, to restart those circuits.
        """
        self._device.SetWireInValue(0x00, 0x02) # reset_fifo = 1. To reset FIFO only
        self._device.UpdateWireIns()
        self._device.SetWireInValue(0x00, 0x00) # de-assertion reset_fifo signal
        self._device.UpdateWireIns()
        time.sleep(0.001) # After Reset de-assertion, wait at least 30 clock cycles before asserting WE/RE signals.
        self._device.SetWireInValue(0x00, 0x01) # reset = 1. To reset other circuits.
        self._device.UpdateWireIns()
        self._device.SetWireInValue(0x00, 0x00) # de-assertion reset signal
        self._device.UpdateWireIns()
    
    def clear_dev(self):
        """ 
        Set reset signals of fifo and counting circuits to 1s, to reset those circuits,
        without de-asserting the reset signals to 0s. Those circuits are reset without restart.
        """
        self._device.SetWireInValue(0x00, 0x02) # reset_fifo = 1. To reset FIFO only
        self._device.UpdateWireIns()
        # time.sleep(0.001) # After Reset de-assertion, wait at least 30 clock cycles before asserting WE/RE signals.
        self._device.SetWireInValue(0x00, 0x01) # reset = 1. To reset other circuits.
        self._device.UpdateWireIns()

    def start_photon_count(self):
        self.lock_in = 0 #not lock_in.
        self._device.SetWireInValue(0x02, int(self.lock_in))
        self._device.SetWireInValue(0x01, int(round(self.counting_period / self.clock_period))) #counting_period, in the unit of counting clock.
        self._device.SetWireInValue(0x03, int(self.lockin_up_period / self.clock_period)) #lockin_up_period, in the unit of counting clock.
        self._device.SetWireInValue(0x04, int(self.lockin_down_period / self.clock_period)) #lockin_down_period, in the unit of counting clock.
        self._device.SetWireInValue(0x05, int(self.lockin_up_rate))
        self._device.SetWireInValue(0x06, int(self.lockin_down_rate))
        self._device.SetWireInValue(0x07, int(self.lockin_updown_ratio_compensate))
        self._device.UpdateWireIns()
        self.reset_dev()
    
    def start_lockin_count(self):
        self.lock_in = 1 #lock_in.
        self._device.SetWireInValue(0x02, int(self.lock_in))
        self._device.SetWireInValue(0x01, int(self.counting_period / self.clock_period)) #counting_period, in the unit of counting clock.
        self._device.SetWireInValue(0x03, int(self.lockin_up_period / self.clock_period)) #lockin_up_period, in the unit of counting clock.
        self._device.SetWireInValue(0x04, int(self.lockin_down_period / self.clock_period)) #lockin_down_period, in the unit of counting clock.
        self._device.SetWireInValue(0x05, int(self.lockin_up_rate))
        self._device.SetWireInValue(0x06, int(self.lockin_down_rate))
        self._device.SetWireInValue(0x07, int(self.lockin_updown_ratio_compensate))
        self._device.UpdateWireIns()
        self.reset_dev()
        
    def pipe_out(self, buff):
        self._device.ReadFromPipeOut(0xA0, buff) 
        

# here are demos for the using this module.        
if __name__ == '__main__':
    dev = XEM7305_photon_counter()
    k = 0
    psize = 16
    buff = [bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize), bytearray(4*psize)]
    ia_out = [[], [], [], [], [], [], [], [], []]  #arrays of integers. the counting results. 

    #demo1: start the counter on FPGA, then pipeout 9 times the counted values.
    dev.counting_period = 1e8/8 #Unit of periods: ns.
    dev.lockin_up_period = 5e7
    dev.lockin_down_period = 5e7
    
    #dev.start_photon_count()
    dev.start_lockin_count()
    NTEST = 3
    while (k < NTEST):
        dev.pipe_out(buff[k])
        k = k+1
    
    pre_value = 0
    for j in range(NTEST):
        for i in range(psize):
            cur_value = int.from_bytes(buff[j][i*4:i*4+4], "little")
            if (dev.lock_in == 1 and cur_value > 4200000000): # under flow processing: hard-coding. Might have better solution.
                cur_value = cur_value - 4294967296 
            ia_out[j].append(cur_value)
            
            # Codes to check the wrong count for dev.counting_period = 100000 and pulse frequency 50MHz
            # if (cur_value - pre_value >= 0 and (cur_value - pre_value > 550 or cur_value - pre_value < 450)):
                # print("error: #ia, #elem, p, c0, c: ", j, i, pre_value, cur_value)
            # elif (cur_value - pre_value < 0 and (pre_value - cur_value > 550 or pre_value - cur_value < 450)):
                # print("error: #ia, #elem, p, c0, c: ", j, i, pre_value, cur_value)
            
            pre_value = cur_value
        
        
    print(buff[0])
    print(buff[1])
    print(buff[2])
    
    print("ia[0]")
    print(ia_out[0])
    print("ia[1]")
    print(ia_out[1])
    print("ia[2]")
    print(ia_out[2])

    
    del dev # if it is not deleted explicitly here, Spyder environment will hold the "dev" object. Then re-run this program in Spyder will crash because the environment think the device is in using by other program.
