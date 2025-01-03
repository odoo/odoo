# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection
from re import sub
from threading import Lock

from odoo.addons.hw_drivers.interface import Interface

conn = CupsConnection()
PPDs = conn.getPPDs()
cups_lock = Lock()  # We can only make one call to Cups at a time


class PrinterInterface(Interface):
    _loop_delay = 120
    connection_type = 'printer'
    printer_devices = {}

    def get_devices(self):
        with cups_lock:
            printers = conn.getPrinters()

        discovered_printers = {
            printer_name: {
                'identifier': printer_name,
                'name': printer_info['printer-info'],
                'connection_type': 'direct' if 'usb' in printer_info['device-uri'] else 'network',
                'url': printer_info['device-uri'],
                'disconnect_counter': self.printer_devices.get(printer_name, {}).get('disconnect_counter', 0),
                'protocol': printer_info.get('device-id', ''),
            }
            for printer_name, printer_info in printers.items()
            if printer_info['printer-info'] != 'unknown'
        }

        # If old devices are not detected 3 times consecutively, they are made unavailable
        self.printer_devices.update(discovered_printers)
        return {
            name: printer
            for name, printer in self.printer_devices.items()
            if name in discovered_printers or printer['disconnect_counter'] < 3
        }
