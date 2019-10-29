from cups import Connection as cups_connection
from re import sub
from threading import Lock

from odoo.addons.hw_drivers.controllers.driver import Interface

conn = cups_connection()
PPDs = conn.getPPDs()
printers = conn.getPrinters()
cups_lock = Lock()  # We can only make one call to Cups at a time

class PrinterInterface(Interface):
    _loop_delay = 120
    connection_type = 'printer'

    def get_devices(self):
        printer_devices = {}
        with cups_lock:
            devices = conn.getDevices()
        for path in devices:
            if 'uuid=' in path:
                identifier = sub('[^a-zA-Z0-9 ]+', '', path.split('uuid=')[1])
            elif 'serial=' in path:
                identifier = sub('[^a-zA-Z0-9 ]+', '', path.split('serial=')[1])
            else:
                identifier = sub('[^a-zA-Z0-9 ]+', '', path)
            devices[path]['identifier'] = identifier
            devices[path]['url'] = path
            printer_devices[identifier] = devices[path]
        return printer_devices
