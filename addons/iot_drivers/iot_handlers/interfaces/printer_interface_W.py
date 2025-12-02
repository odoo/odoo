# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from threading import Lock
import win32print

from odoo.addons.iot_drivers.interface import Interface

_logger = logging.getLogger(__name__)

win32print_lock = Lock()  # Calling win32print in parallel can cause failed prints


class PrinterInterface(Interface):
    _loop_delay = 30
    connection_type = 'printer'

    def get_devices(self):
        printer_devices = {}
        with win32print_lock:
            printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)

            for printer in printers:
                identifier = printer[2]
                handle_printer = win32print.OpenPrinter(identifier)
                # The value "2" is the level of detail we want to get from the printer, see:
                # https://learn.microsoft.com/en-us/windows/win32/printdocs/getprinter#parameters
                printer_details = win32print.GetPrinter(handle_printer, 2)
                printer_port = None
                if printer_details:
                    # see: https://learn.microsoft.com/en-us/windows/win32/printdocs/printer-info-2#members
                    printer_port = printer_details.get('pPortName')
                if printer_port is None:
                    _logger.warning('Printer "%s" has no port name. Used dummy port', identifier)
                    printer_port = 'IOT_DUMMY_PORT'

                if printer_port == "PORTPROMPT:":
                    # discard virtual printers (like "Microsoft Print to PDF") as they will trigger dialog boxes prompt
                    continue

                printer_devices[identifier] = {
                    'identifier': identifier,
                    'printer_handle': handle_printer,
                    'port': printer_port,
                }
        return printer_devices
