from abc import ABC, abstractmethod
from base64 import b64decode
import io
import logging
from PIL import Image, ImageOps
import re
import time

from odoo.addons.iot_drivers.driver import Driver
from odoo.addons.iot_drivers.main import iot_devices
from odoo.addons.iot_drivers.event_manager import event_manager

_logger = logging.getLogger(__name__)


class PrinterDriverBase(Driver, ABC):
    connection_type = 'printer'
    job_timeout_seconds = 30

    RECEIPT_PRINTER_COMMANDS = {
        'star': {
            'center': b'\x1b\x1d\x61\x01',  # ESC GS a n
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

    def __init__(self, identifier, device):
        super().__init__(identifier, device)

        self.device_type = 'printer'
        self.job_ids = []
        self.job_action_ids = {}

        self._actions.update({
            'cashbox': self.open_cashbox,
            'print_receipt': self.print_receipt,
            'status': self.print_status,
            '': self._action_default,
        })

    @classmethod
    def get_status(cls):
        status = 'connected' if any(
            iot_devices[d].device_type == "printer"
            and iot_devices[d].device_connection == 'direct'
            for d in iot_devices
        ) else 'disconnected'
        return {'status': status, 'messages': ''}

    def send_status(self, status, message=None, action_unique_id=None):
        """Sends a status update event for the printer.

        :param str status: The value of the status
        :param str message: A comprehensive message describing the status
        :param str action_unique_id: The unique identifier of the action
        """
        if status == "error":
            self._recent_action_ids.pop(action_unique_id, None)  # avoid filtering duplicates on errors
        self.data['status'] = status
        self.data['message'] = message
        event_manager.device_changed(self, {'session_id': self.data.get('owner')})

    def print_receipt(self, data):
        _logger.debug("print_receipt called for printer %s", self.device_name)

        receipt = b64decode(data['receipt'])
        im = Image.open(io.BytesIO(receipt))

        # Convert to greyscale then to black and white
        im = im.convert("L")
        im = ImageOps.invert(im)
        im = im.convert("1")

        print_command = getattr(self, 'format_%s' % self.receipt_protocol)(im)
        self.print_raw(print_command, action_unique_id=data.get("action_unique_id"))

    @classmethod
    def format_escpos_bit_image_raster(cls, im):
        """ prints with the `GS v 0`-command """
        width = int((im.width + 7) / 8)

        raster_send = b'\x1d\x76\x30\x00'
        max_slice_height = 255

        raster_data = b''
        dots = im.tobytes()
        while len(dots):
            im_slice = dots[:width * max_slice_height]
            slice_height = int(len(im_slice) / width)
            raster_data += raster_send + width.to_bytes(2, 'little') + slice_height.to_bytes(2, 'little') + im_slice
            dots = dots[width * max_slice_height:]

        return raster_data + cls.RECEIPT_PRINTER_COMMANDS['escpos']['cut']

    @classmethod
    def extract_columns_from_picture(cls, im, line_height):
        # Code inspired from python esc pos library:
        # https://github.com/python-escpos/python-escpos/blob/4a0f5855ef118a2009b843a3a106874701d8eddf/src/escpos/image.py#L73-L89
        width_pixels, height_pixels = im.size
        for left in range(0, width_pixels, line_height):
            box = (left, 0, left + line_height, height_pixels)
            im_chunk = im.transform((line_height, height_pixels), Image.EXTENT, box)
            yield im_chunk.tobytes()

    def format_escpos_bit_image_column(
        self, im, high_density_vertical=True, high_density_horizontal=True, size_scale=100
    ):
        """Prints with the `ESC *`-command
        reference: https://reference.epson-biz.com/modules/ref_escpos/index.php?content_id=88

        :param im: PIL image
        :param high_density_vertical: high density in vertical direction
        :param high_density_horizontal: high density in horizontal direction
        :param size_scale: picture scale in percentage,
        e.g: 50 -> half the size (horizontally and vertically)
        """
        size_scale_ratio = size_scale / 100
        size_scale_width = int(im.width * size_scale_ratio)
        size_scale_height = int(im.height * size_scale_ratio)
        im = im.resize((size_scale_width, size_scale_height))
        # escpos ESC * command print column per column
        # (instead of usual row by row).
        # So we transpose the picture to ease the calculations
        im = im.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)

        # Most of the code here is inspired from python escpos library
        # https://github.com/python-escpos/python-escpos/blob/4a0f5855ef118a2009b843a3a106874701d8eddf/src/escpos/escpos.py#L237C9-L251
        ESC = b'\x1b'
        density_byte = (1 if high_density_horizontal else 0) + \
                       (32 if high_density_vertical else 0)
        nL = im.height & 0xFF
        nH = (im.height >> 8) & 0xFF
        HEADER = ESC + b'*' + bytes([density_byte, nL, nH])

        raster_data = ESC + b'3\x10'  # Adjust line-feed size
        line_height = 24 if high_density_vertical else 8
        for column in self.extract_columns_from_picture(im, line_height):
            raster_data += HEADER + column + b'\n'
        raster_data += ESC + b'2'  # Reset line-feed size
        return raster_data + self.RECEIPT_PRINTER_COMMANDS['escpos']['cut']

    def format_escpos(self, im):
        # Epson support different command to print pictures.
        # We use by default "GS v 0", but it  is incompatible with certain
        # printer models (like TM-U2x0)
        # As we are pretty limited in the information that we have, we will
        # use the printer name to parse some configuration value
        # Printer name examples:
        # EpsonTMM30
        #  -> Print using raster mode
        # TM-U220__IMC_LDV_LDH_SCALE70__
        #  -> Print using column bit image mode (without vertical and
        #  horizontal density and a scale of 70%)

        # Default image printing mode
        image_mode = 'raster'

        options_str = self.device_name.split('__')
        option_str = ""
        if len(options_str) > 2:
            option_str = options_str[1].upper()
            if option_str.startswith('IMC'):
                image_mode = 'column'

        if image_mode == 'raster':
            return self.format_escpos_bit_image_raster(im)

        # Default printing mode parameters
        high_density_vertical = True
        high_density_horizontal = True
        scale = 100

        # Parse the printer name to get the needed parameters
        # The separator need to not be filtered by `get_identifier`
        options = option_str.split('_')
        for option in options:
            if option == 'LDV':
                high_density_vertical = False
            elif option == 'LDH':
                high_density_horizontal = False
            elif option.startswith('SCALE'):
                scale_value_str = re.search(r'\d+$', option)
                if scale_value_str is not None:
                    scale = int(scale_value_str.group())
                else:
                    raise ValueError("Missing printer SCALE parameter integer value in option: " + option)

        return self.format_escpos_bit_image_column(im, high_density_vertical, high_density_horizontal, scale)

    def open_cashbox(self, data):
        """Sends a signal to the current printer to open the connected cashbox."""
        _logger.debug("open_cashbox called for printer %s", self.device_name)

        commands = self.RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
        for drawer in commands['drawers']:
            self.print_raw(drawer, action_unique_id=data.get("action_unique_id"))

    def run(self):
        while True:
            # We monitor ongoing jobs by polling them every second.
            # Ideally we would receive events instead of polling, but unfortunately CUPS
            # events do not trigger with all printers, and win32print has no event mechanism.
            for job_id in self.job_ids:
                self._check_job_status(job_id)
            time.sleep(1)

    @abstractmethod
    def print_raw(self, data, action_unique_id=None):
        """Sends the raw data to the printer.

        :param data: The data to send to the printer
        :param str action_unique_id: The unique identifier of the action
        """
        pass

    @abstractmethod
    def print_status(self, data):
        """Method called to test a printer, printing a status page."""
        pass

    @abstractmethod
    def _action_default(self, data):
        """Action called when no action name is provided in the action data."""
        pass

    @abstractmethod
    def _check_job_status(self, job_id):
        """Method called to poll the status of a print job."""
        pass
