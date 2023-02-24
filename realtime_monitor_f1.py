# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 09:36:30 2023


The "function 1" written be Zhenghan in "realtime_monitoring.py" is improved,
 and saved seperately from the moduel "XEM7305_photon_counter.py".

Please put this file together with the file "XEM7305_photon_counter.py".

Just run this file will get the real time monitoring to "normal counting",
main purpose of this program is to be a real-time monitor for adjusting the position of pinhole

@author: Seigen
      qingyuan.tian@oist.jp, tianqingyuan68@gmail.com
"""

#%% For real-time monitoring (function 1. First written by Zhenghan, modified by Seigen)
# main purpose of this section is to be a real-time monitor for adjusting the position of pinhole

import time
import matplotlib.pyplot as plt
import XEM7305_photon_counter

dev = XEM7305_photon_counter.XEM7305_photon_counter()

PIPEOUT_SIZE = 100 #1024 # const
dev.counting_period = 1000000 #Unit of periods: ns.
NUM_FRAMES = 100000000 # total measuring time equals to NUM_FRAMES * PIPEOUT_SIZE * counting_period

buff = [ bytearray(4*PIPEOUT_SIZE) for _ in range(2)]
ia_out = [ [0] for _ in range(2)]

from matplotlib.animation import FuncAnimation
fig, ax = plt.subplots()
y = []
x = []
pre_value = 0
t0 = time.time()
def animate(k,x,y):
    global pre_value

    dev.pipe_out(buff[1])

    cur_value = int.from_bytes(buff[1][(PIPEOUT_SIZE-1)*4:PIPEOUT_SIZE*4], "little") #only processing one value in a pipeOut array; the last one is better then the first one for realtime monitoring.
    
    # under flow processing: hard-coding. Might have better solution.
    if (dev.lock_in == 1 and cur_value > 42e8):
        cur_value = cur_value - 4294967296
    # over flow processing: hard-coding. Might have better solution.
    if (dev.lock_in != 1 and pre_value > 4e9 and cur_value < 2e8):
        # print("Counter overflowed!")
        ia_out[0][0] = ia_out[0][0] - 4294967296 # When cur_value overflow, only processing pre_value (because we only care the diff between cur_value and pre_value). Otherwise, the subsequent values need overflow processing too.
        
    ia_out[1][0] = cur_value
    pre_value = cur_value

    t = k*PIPEOUT_SIZE*dev.counting_period*1e-9
    y.append(ia_out[1][0]-ia_out[0][0])
    x.append(t)
    ia_out[0][0] = ia_out[1][0] #pre_value updated
        
    
    x = x[-500:]
    y = y[-500:]
    ax.clear()
    line, = ax.plot(x, y)
    ax.set_ylabel('Count per 1024*counting period')
    ax.set_xlabel('timeline/s')

    return line, 
    
dev.start_photon_count()
ani = FuncAnimation(fig, animate, frames=NUM_FRAMES, interval=0,fargs=(x,y), repeat=False) # set interval to 0, let pipeOut() control the timing automatically.
plt.show()

