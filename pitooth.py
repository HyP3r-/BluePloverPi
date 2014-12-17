#!/usr/bin/python2.7

from bluetooth import *
import dbus
import time
import ConfigParser
import shutil

from evdev import *

import keymap


class Bluetooth:
    P_CTRL = 17
    P_INTR = 19

    HOST = 0
    PORT = 1

    def __init__(self, bluetooth_name):
        os.system("hciconfig hci0 class 0x002540")
        os.system("hciconfig hci0 name " + bluetooth_name)
        os.system("hciconfig hci0 piscan")
        self.scontrol = BluetoothSocket(L2CAP)
        self.sinterrupt = BluetoothSocket(L2CAP)
        self.scontrol.bind(("", Bluetooth.P_CTRL))
        self.sinterrupt.bind(("", Bluetooth.P_INTR))
        self.bus = dbus.SystemBus()

        self.manager = dbus.Interface(self.bus.get_object("org.bluez", "/"),
                                      "org.bluez.Manager")
        adapter_path = self.manager.DefaultAdapter()
        self.service = dbus.Interface(
            self.bus.get_object("org.bluez", adapter_path), "org.bluez.Service")

        with open(sys.path[0] + "/sdp_record.xml", "r") as fh:
            self.service_record = fh.read()

    def listen(self):
        self.service_handle = self.service.AddRecord(self.service_record)
        print "Service record added"
        self.scontrol.listen(1)  # Limit of 1 connection
        self.sinterrupt.listen(1)
        print "Waiting for a connection"
        self.ccontrol, self.cinfo = self.scontrol.accept()
        print "Got a connection on the control channel from " + self.cinfo[
            Bluetooth.HOST]
        self.cinterrupt, self.cinfo = self.sinterrupt.accept()
        print "Got a connection on the interrupt channel fro " + self.cinfo[
            Bluetooth.HOST]

    def send_input(self, ir):
        # Convert the hex array to a string
        hex_str = ""
        for element in ir:
            if type(element) is list:
                # This is our bit array - convrt it to a single byte represented
                # as a char
                bin_str = ""
                for bit in element:
                    bin_str += str(bit)
                hex_str += chr(int(bin_str, 2))
            else:
                # This is a hex value - we can convert it straight to a char
                hex_str += chr(element)
        # Send an input report
        self.cinterrupt.send(hex_str)


class Keyboard():
    def __init__(self, input_name):
        # The structure for an bt keyboard input report (size is 10 bytes)
        self.state = [
            0xA1,  # This is an input report
            0x01,  # Usage report = Keyboard
            # Bit array for Modifier keys
            [0,  # Right GUI - (usually the Windows key)
             0,  # Right ALT
             0,  # Right Shift
             0,  # Right Control
             0,  # Left GUI - (again, usually the Windows key)
             0,  # Left ALT
             0,  # Left Shift
             0],  # Left Control
            0x00,  # Vendor reserved
            0x00,  # Rest is space for 6 keys
            0x00,
            0x00,
            0x00,
            0x00,
            0x00]

        # Keep trying to get a keyboard
        have_dev = False
        while not have_dev:
            try:
                # Try and get a keyboard - should always be event0 as we.re only
                # plugging one thing in
                self.dev = InputDevice("/dev/input/" + input_name)
                have_dev = True
            except OSError:
                print "Keyboard not found, waiting 3 seconds and retrying"
                time.sleep(3)
            print "Found a keyboard"

    def change_state(self, event):
        evdev_code = ecodes.KEY[event.code]
        modkey_element = keymap.modkey(evdev_code)
        if modkey_element > 0:
            # Need to set one of the modifier bits
            if self.state[2][modkey_element] == 0:
                self.state[2][modkey_element] = 1
            else:
                self.state[2][modkey_element] = 0
        else:
            # Get the hex keycode of the key
            hex_key = keymap.convert(evdev_code)
            # Loop through elements 4 to 9 of the input report structure
            for i in range(4, 10):
                if self.state[i] == hex_key and event.value == 0:
                    # Code is 0 so we need to depress it
                    self.state[i] = 0x00
                    break
                elif self.state[i] == 0x00 and event.value == 1:
                    # If the current space is empty and the key is being pressed
                    self.state[i] = hex_key
                    break

    def event_loop(self, bt):
        for event in self.dev.read_loop():
            # Only bother if we hit a key and it's an up or down event
            if event.type == ecodes.EV_KEY and event.value < 2:
                self.change_state(event)
                bt.send_input(self.state)


if __name__ == "__main__":
    # Help Text
    help_text = """Python Bluetooth Keyboard:
    config: Configure the Bluetooth Keyboard
    stop: Stops the Bluetooth Keyboard
    start: Starts the Bluetooth Keyboard"""

    # File Paths
    filename_config = sys.path[0] + "/config.cfg"
    filename_main = "/etc/bluetooth/main.conf"
    filename_main_backup = "/etc/bluetooth/main.conf.bak"

    if not os.geteuid() == 0:  # Check if Root
        sys.exit("Only root can run this script")

    elif len(sys.argv) != 2:  # Check Length of args
        print(help_text)

    elif sys.argv[1] == "config":  # Configure System
        # Get Available Inputs
        print("Available Input Events:")
        dir_names = list(os.walk("/sys/class/input"))[0][1]
        dir_names = filter(lambda name: "event" in name, dir_names)
        for dir_name in dir_names:
            with open("/sys/class/input/" + dir_name + "/device/name",
                      "r") as fh:
                print(dir_name + ": " + fh.read().strip())
        print("Please choose the Input Event you want (e.g. event0):")
        input_name = sys.stdin.readline().strip()

        # Get Bluetooth Name
        print("Please insert a name for the bluetooth keyboard:")
        bluetooth_name = sys.stdin.readline().strip()

        # Write Config
        config = ConfigParser.RawConfigParser()
        config.add_section("PiBlueBoard")
        config.set("PiBlueBoard", "input", input_name)
        config.set("PiBlueBoard", "name", bluetooth_name)
        with open(filename_config, "wb") as configfile:
            config.write(configfile)

        # Backup main.conf
        shutil.copyfile(filename_main,
                        filename_main_backup)

        # Prepare main.conf
        config = ConfigParser.RawConfigParser()
        config.read(filename_main)
        config.set("General", "DisablePlugins",
                   "network,input,audio,pnat,sap,serial")
        with open(filename_main, "wb") as configfile:
            config.write(configfile)

        # Restart the bluetooth daemon
        os.system("service bluetooth restart")

    elif sys.argv[1] == "stop":  # Configure System
        # Restore Backup
        shutil.copyfile(filename_main_backup,
                        filename_main)
        # Restart the bluetooth daemon
        os.system("service bluetooth restart")

    elif sys.argv[1] == "start":  # Start the System
        # Load configuration
        config = ConfigParser.RawConfigParser()
        config.read(filename_config)
        input_name = config.get("PiBlueBoard", "input")
        bluetooth_name = config.get("PiBlueBoard", "name")

        # Start the System
        bluetooth = Bluetooth(bluetooth_name)
        bluetooth.listen()
        keyboard = Keyboard(input_name)
        keyboard.event_loop(bluetooth)
    else:
        print(help_text)

