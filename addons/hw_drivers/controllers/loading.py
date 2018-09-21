import importlib.util
import os
driversList = os.listdir("/home/pi/odoo/addons/hw_drivers/drivers")

path = "/home/pi/odoo/addons/hw_drivers/"
driver = "driver.py"
spec = importlib.util.spec_from_file_location(driver, path)
if spec:
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
for driver in driversList:
    #from ..drivers import driver
    path = "/home/pi/odoo/addons/hw_drivers/drivers/" + driver
    spec = importlib.util.spec_from_file_location(driver, path)
    if spec:
        foo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(foo)