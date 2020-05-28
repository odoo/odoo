from cups import Connection as cups_connection
from re import sub
from threading import Lock

from odoo.addons.hw_drivers.controllers.driver import Interface

conn = cups_connection()
PPDs = conn.getPPDs()
cups_lock = Lock()  # We can only make one call to Cups at a time

class PrinterInterface(Interface):
    _loop_delay = 120
    connection_type = 'printer'

    def get_devices(self):
        printer_devices = {}
        with cups_lock:
            printers = conn.getPrinters()
            for printer in printers:
                printers[printer]['supported'] = True # these printers are automatically supported
                printers[printer]['device-make-and-model'] = printers[printer]['printer-make-and-model']
                if 'usb' in printers[printer]['device-uri']:
                    printers[printer]['device-class'] = 'direct'
                else:
                    printers[printer]['device-class'] = 'network'
            devices = conn.getDevices()
            if printers:
                devices.update(printers)
        for path in devices:
            if 'uuid=' in path:
                identifier = sub('[^a-zA-Z0-9_]', '', path.split('uuid=')[1])
            elif 'serial=' in path:
                identifier = sub('[^a-zA-Z0-9_]', '', path.split('serial=')[1])
            else:
                identifier = sub('[^a-zA-Z0-9_]', '', path)
            devices[path]['identifier'] = identifier
            devices[path]['url'] = path
            printer_devices[identifier] = devices[path]
        return printer_devices
