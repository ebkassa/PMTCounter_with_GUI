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

ok*:							Opal Kelly API files for python3.7

firmware/*:					firmware source codes


Requirments
-----------
Python3.7 or later

PyQt5

pyqtgraph


Usage
-----
python PMTCounter_GUI.py

Note for Linux usage
-----
First running attempt failed. Error: No module named '_ok'
It turns out the ok.pyd file is for windows and one need ok.so for linux.

One can 
download FrontPanel-Ubuntu20.04LTS-x64-5.2.11.tgz from
https://office365oist.sharepoint.com/sites/OISTEQuIPUnit 

Then replace the files ok.py and _ok.pyd in the cloned github files with ok.py and _ok.so from the sharepoint folder. 

Note on pyqt
-----

One may get an error if using pyqtgraph 0.11.1
versions 0.12 and above should work. 
It sufficed to update pyqt to the latest version (5.15.x)




