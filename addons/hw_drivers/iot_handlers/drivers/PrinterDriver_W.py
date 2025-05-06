# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from base64 import b64decode
import io
import win32print
import ghostscript

from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.iot_handlers.drivers.printer_driver_base import PrinterDriverBase
from odoo.addons.hw_drivers.tools import helpers
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)


class PrinterDriver(PrinterDriverBase):

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_connection = self._compute_device_connection(device)
        self.device_name = device.get('identifier')
        self.printer_handle = device.get('printer_handle')

        self.receipt_protocol = 'escpos'
        if any(cmd in device['identifier'] for cmd in ['STAR', 'Receipt']):
            self.device_subtype = "receipt_printer"
        elif "ZPL" in device['identifier']:
            self.device_subtype = "label_printer"
        else:
            self.device_subtype = "office_printer"

    @classmethod
    def supported(cls, device):
        # discard virtual printers (like "Microsoft Print to PDF") as they will trigger dialog boxes prompt
        return device['port'] != 'PORTPROMPT:'

    @staticmethod
    def _compute_device_connection(device):
        return 'direct' if device['port'].startswith(('USB', 'COM', 'LPT')) else 'network'

    def disconnect(self):
        self.update_status('disconnected', 'Printer was disconnected')
        super(PrinterDriver, self).disconnect()

    def print_raw(self, data):
        win32print.StartDocPrinter(self.printer_handle, 1, ('', None, "RAW"))
        win32print.StartPagePrinter(self.printer_handle)
        win32print.WritePrinter(self.printer_handle, data)
        win32print.EndPagePrinter(self.printer_handle)
        win32print.EndDocPrinter(self.printer_handle)

    def print_report(self, data):
        helpers.write_file('document.pdf', data, 'wb')
        file_name = helpers.path_file('document.pdf')
        printer = self.device_name

        args = [
            "-dPrinted", "-dBATCH", "-dNOPAUSE", "-dNOPROMPT",
            "-q",
            "-sDEVICE#mswinpr2",
            f'-sOutputFile#%printer%{printer}',
            f'{file_name}'
        ]

        _logger.debug("Printing report with ghostscript using %s", args)
        stderr_buf = io.BytesIO()
        stdout_buf = io.BytesIO()
        stdout_log_level = logging.DEBUG
        try:
            ghostscript.Ghostscript(*args, stdout=stdout_buf, stderr=stderr_buf)
        except Exception:
            _logger.exception("Error while printing report, ghostscript args: %s, error buffer: %s", args, stderr_buf.getvalue())
            stdout_log_level = logging.ERROR # some stdout value might contains relevant error information
            raise
        finally:
            _logger.log(stdout_log_level, "Ghostscript stdout: %s", stdout_buf.getvalue())

    def _action_default(self, data):
        _logger.debug("_action_default called for printer %s", self.device_name)

        document = b64decode(data['document'])
        mimetype = guess_mimetype(document)
        if mimetype == 'application/pdf':
            self.print_report(document)
        else:
            self.print_raw(document)
        _logger.debug("_action_default finished with mimetype %s for printer %s", mimetype, self.device_name)
        return {'print_id': data['print_id']}

    def print_status(self, _data=None):
        """Prints the status ticket of the IoT Box on the current printer.

        :param _data: dict provided by the action route
        """
        if self.device_subtype == "receipt_printer":
            commands = self.RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
            self.print_raw(commands['center'] + (commands['title'] % b'IoT Box Test Receipt') + commands['cut'])
        elif self.device_type == "label_printer":
            self.print_raw("^XA^CI28 ^FT35,40 ^A0N,30 ^FDIoT Box Test Label^FS^XZ".encode())
        else:
            self.print_raw("IoT Box Test Page".encode())


proxy_drivers['printer'] = PrinterDriver
