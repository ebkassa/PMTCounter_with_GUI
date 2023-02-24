# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 09:36:30 2023


The "function 2" written be Zhenghan in "realtime_monitoring.py" is improved,
 and saved seperately from the moduel "XEM7305_photon_counter.py".

Please put this file together with the file "XEM7305_photon_counter.py".

Just run this file will get the real time monitoring to "lock-in counting",
for taking the lockin count over a certain period of time

@author: Seigen
      qingyuan.tian@oist.jp, tianqingyuan68@gmail.com
"""
# %% real-time monitoring with lockin signal (function 2. First written by Zhenghan, modified by Seigen.)
# for taking the lockin count over a certain period of time

#import time
import matplotlib.pyplot as plt
import XEM7305_photon_counter

dev = XEM7305_photon_counter.XEM7305_photon_counter()

dev.counting_period =1e5
#Unit of periods: ns, the absolute limit of this value is from 0 to 2.1739*2^32 ns 
# however some technical issues may happen if it is set to be really low
#please consult Seigen
dev.lockin_up_period = 1e5*512
dev.lockin_down_period = 1e5*512

# The 512 is because there are 1024 data points per buffer, the lockin period is
# synchronised only if the multiplier is 512 as we take one data point from per 1024 data points. 
# only 50% duty cycle is considered in this case to subtract all the noise

PIPEOUT_SIZE = 1024 # const
NUM_FRAMES = 1000 # total measuring time equals to NUM_FRAMES * PIPEOUT_SIZE * counting_period

buff = [ bytearray(4*PIPEOUT_SIZE) ]
ia_out = [ 0 ]

from matplotlib.animation import FuncAnimation
fig, ax = plt.subplots()
y = []
x = []
def animate(k,x,y):
    
    dev.pipe_out(buff[0])
    
    cur_value = int.from_bytes(buff[0][(PIPEOUT_SIZE-1)*4:PIPEOUT_SIZE*4], "little") #Zhenghun used the first value in a 1024 length array. But I think the last one is better for real time monitoring, because it is the newest. Seigen.
    
    # under flow processing: hard-coding. Might have better solution.
    if (dev.lock_in == 1 and cur_value > 4200000000): 
        cur_value = cur_value - 4294967296

    # over flow processing: lock-in count shold not over-flow.

    ia_out[0] = cur_value

    t = k*1024*dev.counting_period*1e-9
    y.append(ia_out[0])
    x.append(t)

    x = x[-1000:] # to set the number of data points in every frame 
    y = y[-1000:]
    
    ax.clear()
    line, = ax.plot(x, y)
    ax.set_ylabel('Effective Count Accumulated')
    ax.set_xlabel('timeline/s')

    return line, 
    
dev.start_lockin_count() 
#time.sleep(0.1024) # I don't think we need sleep here. But if real experiment needs some sleep time, un-comment it. Seigen.
ani = FuncAnimation(fig, animate, frames=NUM_FRAMES, interval=0,fargs=(x,y), repeat=False) # set interval to 0, let pipeOut() control the timing automatically.
plt.show()