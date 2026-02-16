#Author-Kaustav Gopinathan
#Description-This script runs python code that generates a microfluidic device using the MicroCAD library. Modify this script to select the device to generate.

import adsk.core, adsk.fusion, adsk.cam, traceback
import sys, importlib

device_path = r'C:\Path\To\File\Here'
device_file = 'Amp_Example'

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        sys.path.append(device_path)
        my_device = importlib.import_module(device_file)
        importlib.reload(my_device)
        my_device.main()
        ui.messageBox('Completed {}'.format(device_file))

    except:
        if ui:
            err_msg = traceback.format_exc()
            ui.messageBox('Failed:\n{}'.format(err_msg))
            if len(err_msg) > 800:
                ui.messageBox('Contd:\n{}'.format(err_msg[800:]))
