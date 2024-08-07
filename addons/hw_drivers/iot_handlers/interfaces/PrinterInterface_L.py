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
    printer_devices = {}

    def get_devices(self):
        discovered_devices = {}
        with cups_lock:
            printers = conn.getPrinters()
            devices = conn.getDevices()
            for printer_name, printer in printers.items():
                path = printer.get('device-uri', False)
                if printer_name != self.get_identifier(path):
                    printer.update({'supported': True}) # these printers are automatically supported
                    device_class = 'network'
                    if 'usb' in printer.get('device-uri'):
                        device_class = 'direct'
                    printer.update({'device-class': device_class})
                    printer.update({'device-make-and-model': printer_name}) # give name setted in Cups
                    printer.update({'device-id': ''})
                    devices.update({printer_name: printer})
        for path, device in devices.items():
            identifier = self.get_identifier(path)
            device.update({'identifier': identifier})
            device.update({'url': path})
            device.update({'disconnect_counter': 0})
            discovered_devices.update({identifier: device})
        self.printer_devices.update(discovered_devices)
        # Deal with devices which are on the list but were not found during this call of "get_devices"
        # If they aren't detected 3 times consecutively, remove them from the list of available devices
        for device in list(self.printer_devices):
            if not discovered_devices.get(device):
                disconnect_counter = self.printer_devices.get(device).get('disconnect_counter')
                if disconnect_counter >= 2:
                    self.printer_devices.pop(device, None)
                else:
                    self.printer_devices[device].update({'disconnect_counter': disconnect_counter + 1})
        return dict(self.printer_devices)

    def get_identifier(self, path):
        """
        Necessary because the path is not always a valid Cups identifier,
        as it may contain characters typically found in URLs or paths.

          - Removes characters: ':', '/', '.', '\', and space.
          - Removes the exact strings: "uuid=" and "serial=".

        Example 1:
            Input: "ipp://printers/printer1:1234/abcd"
            Output: "ippprintersprinter11234abcd"

        Example 2:
            Input: "uuid=1234-5678-90ab-cdef"
            Output: "1234-5678-90ab-cdef
        """
        return sub(r'[:\/\.\\ ]|(uuid=)|(serial=)', '', path)
