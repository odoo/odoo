# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection
import logging
from re import sub
from threading import Lock
import time

from odoo.addons.hw_drivers.interface import Interface

conn = CupsConnection()
PPDs = conn.getPPDs()
cups_lock = Lock()  # We can only make one call to Cups at a time
_logger = logging.getLogger(__name__)


class PrinterInterface(Interface):
    connection_type = 'printer'
    _loop_delay = 20  # Default delay between calls to get_devices

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.printer_devices = {}

    def get_devices(self):
        discovered_devices = {}
        with cups_lock:
            printers = conn.getPrinters()
            devices = conn.getDevices()
            for printer_name, printer in printers.items():
                path = printer.get('device-uri', False)
                if printer_name != self.get_identifier(path):
                    device_class = 'direct' if 'usb' in printer.get('device-uri') else 'network'
                    printer.update({
                        'supported': True,
                        'device-class': device_class,
                        'device-make-and-model': printer_name,  # give name set in Cups
                        'device-id': '',
                    })
                    devices.update({printer_name: printer})

        for path, device in devices.items():
            identifier = self.get_identifier(path)
            device.update({
                'identifier': identifier,
                'url': path,
                'disconnect_counter': 0,
            })
            discovered_devices.update({identifier: device})

        self.printer_devices.update(discovered_devices)
        # Let get_devices be called again every 20 seconds (get_devices of PrinterInterface
        # takes between 4 and 15 seconds) but increase the delay to 2 minutes if it has been
        # running for more than 1 hour
        if self.start_time and time.time() - self.start_time > 3600:
            self._loop_delay = 120
            self.start_time = None  # Reset start_time to avoid changing the loop delay again

        # Devices previously discovered but not found this call
        # When the printer disconnects it can still be listed in cups and print after reconnecting
        # Wait for 3 consecutive misses before removing it from the list allows us to avoid errors and unnecessary double prints
        missing = set(self.printer_devices) - set(discovered_devices)
        for identifier in missing:
            printer = self.printer_devices[identifier]
            if printer["disconnect_counter"] >= 2:
                _logger.warning('Printer %s not found 3 times in a row, disconnecting.', identifier)
                self.printer_devices.pop(identifier, None)
            else:
                printer["disconnect_counter"] += 1

        return self.printer_devices.copy()

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
