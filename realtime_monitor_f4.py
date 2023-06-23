# -*- coding: utf-8 -*-
"""
Created on Mon Jan 30 10:57:43 2023

The "function 3" written be Zhenghan in "realtime_monitoring.py" is improved,
 and saved seperately from the moduel "XEM7305_photon_counter.py".

Please put this file together with the file "XEM7305_photon_counter.py".

Just run this file will get the real time monitoring to "differentiate lock-in count plot".

@author: Seigen
      qingyuan.tian@oist.jp, tianqingyuan68@gmail.com
"""

# %% for the wavemeter


import socket
import pickle

# IP address and TCP port of server
host = "192.168.1.30"
port = 5353

# Connect to server, display error if connection fails
ClientSocket = socket.socket()
print("Waiting for connection")
try:
    ClientSocket.connect((host, port))
    print("Connected!")
except socket.error as e:
    print(str(e))

# Define global variable which will store the wavelength
# Starting values are Off
selec_list = [["Off"], ["Off"], ["Off"], ["Off"], ["Off"], ["Off"], ["Off"], ["Off"]]

# select desired channel of wavemeter here
cha_num = 3
selec_list[cha_num - 1] = "On"


# Initial time measurement
ti = time.perf_counter()


# %% Functions

import time
import matplotlib.pyplot as plt
import XEM7305_photon_counter

dev = XEM7305_photon_counter.XEM7305_photon_counter()

dev.counting_period = 1e5
dev.lockin_up_period = 1e5 * 512
dev.lockin_down_period = 1e5 * 512

PIPEOUT_SIZE = 1024  # const
NUM_FRAMES = (
    10  # total measuring time equals to NUM_FRAMES * PIPEOUT_SIZE * counting_period
)

buff = [bytearray(4 * PIPEOUT_SIZE) for _ in range(2)]
ia_out = [[0] for _ in range(2)]

from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots()
# y = []
# x = []
pre_value = 0

signal_list = []
wvl_list = []


def get_signal():
    global pre_value

    dev.pipe_out(buff[1])

    cur_value = int.from_bytes(
        buff[1][(PIPEOUT_SIZE - 1) * 4 : PIPEOUT_SIZE * 4], "little"
    )  # Zhenghun used the first value in a 1024 length array. But I think the last one is better for real time monitoring, because it is the newest. Seigen.

    # under flow processing: hard-coding. Might have better solution.
    if dev.lock_in == 1 and cur_value > 4200000000:
        cur_value = cur_value - 4294967296

    # over flow processing: lock-in count shold not over-flow.

    ia_out[1][0] = cur_value
    pre_value = cur_value  # pre_value updated

    signal = ia_out[1][0] - ia_out[0][0]
    # t = k * 1024 * dev.counting_period * 1e-9
    # y.append(ia_out[1][0] - ia_out[0][0])
    # x.append(t)
    ia_out[0][0] = ia_out[1][0]  # pre_value updated

    return signal


def get_wavelength():
    # Pickles and sends selection list
    to_send = pickle.dumps(selec_list)
    ClientSocket.sendall(to_send)
    # Reads in the length of the message to be received
    length = ClientSocket.recv(8).decode()

    msg = []
    # # Reads data sent from the host, stores in msg until full message is received
    while len(b"".join(msg)) < int(length):
        temp = ClientSocket.recv(8192)
        msg.append(temp)

    # Unpickle msg
    data = pickle.loads(b"".join(msg))

    # Store wavelength and interferometer data in separate lists
    wvl_data = data[0]
    # int_data = data[1]

    # cha_num = 7

    # extract wavelength of chosen channel
    selec_cha_wavelength = wvl_data[cha_num - 1]
    # print(selec_cha_wavelength)
    wvl = float(selec_cha_wavelength)

    return wvl


def measure_and_plot():
    signal = get_signal()
    wvl = get_wavelength()

    signal_list.append(signal)
    wvl_list.append(wvl)
    plt.scatter(wvl, signal)


# %% Acquisiton

dev.start_lockin_count()
# time.sleep(0.1024) # I don't think we need sleep here. But if real experiment needs some sleep time, un-comment it. Seigen.
ani = FuncAnimation(
    fig, measure_and_plot, frames=NUM_FRAMES, interval=0, repeat=False
)  # set interval to 0, let pipeOut() control the timing automatically.
plt.show()

# save data
import numpy as np

signal_list = np.array(signal_list)
wvl_list = np.array(wvl_list)
np.savez("data.npz", signal_list=signal_list, wvl_list=wvl_list)

# %% Close connection
ClientSocket.close()
