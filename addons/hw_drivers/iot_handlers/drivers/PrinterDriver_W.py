# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from PIL import Image, ImageOps
import logging
from base64 import b64decode
import io
import win32print
import ghostscript

from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

RECEIPT_PRINTER_COMMANDS = {
    'star': {
        'center': b'\x1b\x1d\x61\x01', # ESC GS a n
        'cut': b'\x1b\x64\x02',  # ESC d n
        'title': b'\x1b\x69\x01\x01%s\x1b\x69\x00\x00',  # ESC i n1 n2
        'drawers': [b'\x07', b'\x1a']  # BEL & SUB
    },
    'escpos': {
        'center': b'\x1b\x61\x01',  # ESC a n
        'cut': b'\x1d\x56\x41\n',  # GS V m
        'title': b'\x1b\x21\x30%s\x1b\x21\x00',  # ESC ! n
        'drawers': [b'\x1b\x3d\x01', b'\x1b\x70\x00\x19\x19', b'\x1b\x70\x01\x19\x19']  # ESC = n then ESC p m t1 t2
    }
}

class PrinterDriver(Driver):
    connection_type = 'printer'

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'printer'
        self.device_connection = 'network'
        self.device_name = device.get('identifier')
        self.printer_handle = device.get('printer_handle')
        self.state = {
            'status': 'connecting',
            'message': 'Connecting to printer',
            'reason': None,
        }
        self.send_status()

        self._actions.update({
            'cashbox': self.open_cashbox,
            'print_receipt': self.print_receipt,
            '': self._action_default,
        })

        self.receipt_protocol = 'escpos'

    @classmethod
    def supported(cls, device):
        return True

    @classmethod
    def get_status(cls):
        status = 'connected' if any(iot_devices[d].device_type == "printer" and iot_devices[d].device_connection == 'direct' for d in iot_devices) else 'disconnected'
        return {'status': status, 'messages': ''}

    def disconnect(self):
        self.update_status('disconnected', 'Printer was disconnected')
        super(PrinterDriver, self).disconnect()

    def update_status(self, status, message, reason=None):
        """Updates the state of the current printer.

        Args:
            status (str): The new value of the status
            message (str): A comprehensive message describing the status
            reason (str): The reason fo the current status
        """
        if self.state['status'] != status or self.state['reason'] != reason:
            self.state = {
                'status': status,
                'message': message,
                'reason': reason,
            }
            self.send_status()

    def send_status(self):
        """ Sends the current status of the printer to the connected Odoo instance.
        """
        self.data = {
            'value': '',
            'state': self.state,
        }
        event_manager.device_changed(self)

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
            "-dPrinted", "-dBATCH", "-dNOPAUSE", "-dNOPROMPT"
            "-q",
            "-sDEVICE#mswinpr2",
            f'-sOutputFile#%printer%{printer}',
            f'{file_name}'
            ]

        ghostscript.Ghostscript(*args)

    def print_receipt(self, data):
        receipt = b64decode(data['receipt'])
        im = Image.open(io.BytesIO(receipt))

        # Convert to greyscale then to black and white
        im = im.convert("L")
        im = ImageOps.invert(im)
        im = im.convert("1")

        print_command = getattr(self, 'format_%s' % self.receipt_protocol)(im)
        self.print_raw(print_command)

    def format_escpos(self, im):
        width = int((im.width + 7) / 8)

        raster_send = b'\x1d\x76\x30\x00'
        max_slice_height = 255

        raster_data = b''
        dots = im.tobytes()
        while dots:
            im_slice = dots[:width*max_slice_height]
            slice_height = int(len(im_slice) / width)
            raster_data += raster_send + width.to_bytes(2, 'little') + slice_height.to_bytes(2, 'little') + im_slice
            dots = dots[width*max_slice_height:]

        return raster_data + RECEIPT_PRINTER_COMMANDS['escpos']['cut']

    def open_cashbox(self, data):
        """Sends a signal to the current printer to open the connected cashbox."""
        commands = RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
        for drawer in commands['drawers']:
            self.print_raw(drawer)

    def _action_default(self, data):
        document = b64decode(data['document'])
        mimetype = guess_mimetype(document)
        if mimetype == 'application/pdf':
            self.print_report(document)
        else:
            self.print_raw(document)

proxy_drivers['printer'] = PrinterDriver
