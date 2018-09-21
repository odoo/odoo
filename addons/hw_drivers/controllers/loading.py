import importlib.util
import os
from driver import BtManager
from driver import USBDeviceManager
driversList = os.listdir("/home/pi/odoo/addons/hw_drivers/drivers")

# Driver automatically loaded from the posbox homepage

#path = "/home/pi/odoo/addons/hw_drivers/"
#driver = "driver.py"
#spec = importlib.util.spec_from_file_location(driver, path)
#if spec:
#    foo = importlib.util.module_from_spec(spec)
#    spec.loader.exec_module(foo)
for driver in driversList:
    #from ..drivers import driver
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

udm = USBDeviceManager()
udm.daemon = True
udm.start()
