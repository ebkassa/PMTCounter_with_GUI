
# Description

- The project implements a PMT counter by using an Opal Kelly XEM7305 FPGA board.
---

# What is new
- The newest version is V2 (2023-3-30). 
- It is used to output and draw 2 plots (one for normal counting, another for lock-in counting) at the same time. It is not compatible to previous versions. The _V2.py codes can only run with _V2.bit file.
---


# File Description

## Version GUI_V2:
- PMTCounter_GUI_V2.py:			python program of the GUI for the counter
- XEM7305_photon_counter_V2.py:	python module of the counter
- photon_counter_V2.bit:			compiled firmware for the counter
---

## Version: GUI (V1):
- PMTCounter_GUI.py:			python program of the GUI for the counter
- XEM7305_photon_counter.py:	python module of the counter
- photon_counter_GUI.bit:		compiled firmware for the counter
---

## Version: proto-type without GUI:
- XEM7305_photon_counter.py:	python module of the counter (same module file as above, compatible with photon_counter.bit)
- realtime_monitor_*.py:		python program for testing the proto-type
- photon_counter_sample.py:	python program for testing the proto-type
- photon_counter.bit:			compiled firmware for testing the proto-type
---

## API:
- ok*, _ok*:					Opal Kelly API files for python3.7 (for Windows)
- ok.so               Opal Kelly API files for python3.7 (for Linux, refer to "Note for Linux usage" below)
---

## Fireware:
- firmware/*:					firmware source codes for V2
---


# Requirments
- Python3.7 or later
- PyQt5
- pyqtgraph 0.12 or later
---

# Usage
                 python PMTCounter_GUI_V2.py
---


# Note for Linux usage
---
First running attempt failed. Error: No module named '_ok'
It turns out the ok.pyd file is for windows and one need ok.so for linux.

One can 
download FrontPanel-Ubuntu20.04LTS-x64-5.2.11.tgz from
https://office365oist.sharepoint.com/sites/OISTEQuIPUnit 

Then replace the files ok.py and _ok.pyd in the cloned github files with ok.py and _ok.so from the sharepoint folder. 

# Note on pyqt
-----

One may get an error if using pyqtgraph 0.11.1
versions 0.12 and above should work. 
It sufficed to update pyqt to the latest version (5.15.x)




