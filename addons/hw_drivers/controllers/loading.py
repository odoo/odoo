import importlib.util
import os
from odoo.addons.hw_drivers.controllers.driver import BtManager
from odoo.addons.hw_drivers.controllers.driver import USBDeviceManager

driversList = os.listdir("/home/pi/odoo/addons/hw_drivers/drivers")
for driver in driversList:
    path = "/home/pi/odoo/addons/hw_drivers/drivers/" + driver
    spec = importlib.util.spec_from_file_location(driver, path)
    if spec:
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)


#----------------------------------------------------------
#Bluetooth start
#----------------------------------------------------------
bm = BtManager()
bm.daemon = True
bm.start()

#----------------------------------------------------------
#USB start
#----------------------------------------------------------

udm = USBDeviceManager()
udm.daemon = True
udm.start()
