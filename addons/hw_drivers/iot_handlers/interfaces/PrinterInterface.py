# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as cups_connection
from re import sub
from threading import Lock

from odoo.addons.hw_drivers.interface import Interface

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
            devices = conn.getDevices()
            for printer in printers:
                path = printers.get(printer).get('device-uri', False)
                if path and path in devices:
                    devices.get(path).update({'supported': True}) # these printers are automatically supported
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
