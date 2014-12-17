PyBlueBoard
===========

Using Computer as Bluetooth Keyboard for Smartphone

Install
=======

First install some packages with apt:

apt-get update
apt-get install python-gobject bluez bluez-tools \
                python-bluez python-dev \
                python-pip bluez-utils bluez-compat bluetooth

Then this package with pip:

pip install evdev

Usage
=====

You have to run this with root:

sudo ./pitooth.py -config

There are following command line arguments available:

config: Configure the Bluetooth Keyboard
        You can set the name for the bluetooth device and
        the input device (usually a keyboard).
stop: Stops the Bluetooth Keyboard
      This restores the bluetooth config file.
start: Starts the Bluetooth Keyboard
       Starts the listener, your computer is now visible to for the
       Smartphone, you can connect.

Known Problems
==============

Under Ubuntu there are several daemons running, which are using bluetooth.

After you run config, there should be nothing listed when you run following:

sudo sdptool browse local

Tested Systems
==============

This little program was successfully tested on following Systems:

* Ubuntu 14.04 3.13.0-43-generic x86_64 x86_64 x86_64

What could be improved?
=======================

* Argument evaluation while startup
* More testing
* Install Script (Makefile)
* More Exception Handling
* Change to Python3 (Bluetooth is missing)