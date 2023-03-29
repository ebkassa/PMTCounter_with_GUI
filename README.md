README
===========
Description
-----------
The project implements a PMT counter by using an Opal Kelly XEM7305 FPGA board.


File:						Description

PMTCounter_GUI.py:			python program of the GUI for the counter

XEM7305_photon_counter.py:	python module of the counter

photon_counter_gui.bit:		compiled firmware for the counter

realtime_monitor_*.py:		python program for testing the proto-type

photon_counter_sample.py:	python program for testing the proto-type

photon_counter.bit:			compiled firmware for testing the proto-type

ok*, _ok*:					Opal Kelly API files for python3.7 (for Windows)

firmware/*:					firmware source codes

>>>>>>> e5e2404beef82df46390eb86e2714c8a001d3e01

Requirments
-----------
Python3.7 or later

PyQt5

pyqtgraph 0.12 or later



Usage
-----
python PMTCounter_GUI.py
