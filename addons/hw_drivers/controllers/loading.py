import importlib.util
import os
from .driver import BtManager
from .driver import USBDeviceManager
from odoo import modules

driversList = os.listdir("/home/pi/odoo/addons/hw_drivers/drivers")
for driver in driversList:
    path = "/home/pi/odoo/addons/hw_drivers/drivers/" + driver
    spec = importlib.util.spec_from_file_location(driver, path)
    if spec:
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)


if not getattr(modules, '_iot_daemon_started', False):
    # ----------------------------------------------------------
    # Bluetooth start
    # ----------------------------------------------------------
    bm = BtManager()
    bm.daemon = True
    bm.start()

    #----------------------------------------------------------
    #USB start
    #----------------------------------------------------------

    udm = USBDeviceManager()
    udm.daemon = True
    udm.start()

    # Did this because of the
    modules._iot_daemon_started = True

