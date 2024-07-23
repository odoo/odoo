# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from cups import IPPError, IPP_PRINTER_IDLE, IPP_PRINTER_PROCESSING, IPP_PRINTER_STOPPED
import dbus
import io
import logging
import netifaces as ni
from PIL import Image, ImageOps
import re
import subprocess

from odoo import http
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.iot_handlers.interfaces.PrinterInterface_L import PPDs, conn, cups_lock
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers

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

def cups_notification_handler(message, uri, device_identifier, state, reason, accepting_jobs):
    if device_identifier in iot_devices:
        reason = reason if reason != 'none' else None
        state_value = {
            IPP_PRINTER_IDLE: 'connected',
            IPP_PRINTER_PROCESSING: 'processing',
            IPP_PRINTER_STOPPED: 'stopped'
        }
        iot_devices[device_identifier].update_status(state_value[state], message, reason)


# Create a Cups subscription if it doesn't exist yet
try:
    conn.getSubscriptions('/printers/')
except IPPError:
    conn.createSubscription(
        uri='/printers/',
        recipient_uri='dbus://',
        events=['printer-state-changed']
    )

# Listen for notifications from Cups
bus = dbus.SystemBus()
bus.add_signal_receiver(cups_notification_handler, signal_name="PrinterStateChanged", dbus_interface="org.cups.cupsd.Notifier")


class PrinterDriver(Driver):
    connection_type = 'printer'

    def __init__(self, identifier, device):
        super(PrinterDriver, self).__init__(identifier, device)
        self.device_type = 'printer'
        self.device_connection = device['device-class'].lower()
        self.device_name = device['device-make-and-model']
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

        self.receipt_protocol = 'star' if 'STR_T' in device['device-id'] else 'escpos'
        if 'direct' in self.device_connection and any(cmd in device['device-id'] for cmd in ['CMD:STAR;', 'CMD:ESC/POS;']):
            self.print_status()

    @classmethod
    def supported(cls, device):
        if device.get('supported', False):
            return True
        protocol = ['dnssd', 'lpd', 'socket']
        if (
                any(x in device['url'] for x in protocol)
                and device['device-make-and-model'] != 'Unknown'
                or (
                'direct' in device['device-class']
                and 'serial=' in device['url']
        )
        ):
            model = cls.get_device_model(device)
            ppd_file = ''
            for ppd in PPDs:
                if model and model in PPDs[ppd]['ppd-product']:
                    ppd_file = ppd
                    break
            with cups_lock:
                if ppd_file:
                    conn.addPrinter(name=device['identifier'], ppdname=ppd_file, device=device['url'])
                else:
                    conn.addPrinter(name=device['identifier'], device=device['url'])

                conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
                conn.enablePrinter(device['identifier'])
                conn.acceptJobs(device['identifier'])
                conn.setPrinterUsersAllowed(device['identifier'], ['all'])
                conn.addPrinterOptionDefault(device['identifier'], "usb-no-reattach", "true")
                conn.addPrinterOptionDefault(device['identifier'], "usb-unidir", "true")
            return True
        return False

    @classmethod
    def get_device_model(cls, device):
        device_model = ""
        if device.get('device-id'):
            for device_id in [device_lo for device_lo in device['device-id'].split(';')]:
                if any(x in device_id for x in ['MDL', 'MODEL']):
                    device_model = device_id.split(':')[1]
                    break
        elif device.get('device-make-and-model'):
            device_model = device['device-make-and-model']
        return re.sub(r"[\(].*?[\)]", "", device_model).strip()

    @classmethod
    def get_status(cls):
        status = 'connected' if any(
            iot_devices[d].device_type == "printer"
            and iot_devices[d].device_connection == 'direct'
            for d in iot_devices
        ) else 'disconnected'
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
        process = subprocess.Popen(["lp", "-d", self.device_identifier], stdin=subprocess.PIPE)
        process.communicate(data)
        if process.returncode != 0:
            # The stderr isn't meaningful so we don't log it ('No such file or directory')
            _logger.error('Printing failed: printer with the identifier "%s" could not be found',
                          self.device_identifier)

    def print_receipt(self, data):
        receipt = b64decode(data['receipt'])
        im = Image.open(io.BytesIO(receipt))

        # Convert to greyscale then to black and white
        im = im.convert("L")
        im = ImageOps.invert(im)
        im = im.convert("1")

        print_command = getattr(self, 'format_%s' % self.receipt_protocol)(im)
        self.print_raw(print_command)

    def format_star(self, im):
        width = int((im.width + 7) / 8)

        raster_init = b'\x1b\x2a\x72\x41'
        raster_page_length = b'\x1b\x2a\x72\x50\x30\x00'
        raster_send = b'\x62'
        raster_close = b'\x1b\x2a\x72\x42'

        raster_data = b''
        dots = im.tobytes()
        while len(dots):
            raster_data += raster_send + width.to_bytes(2, 'little') + dots[:width]
            dots = dots[width:]

        return raster_init + raster_page_length + raster_data + raster_close

    def format_escpos_bit_image_raster(self, im):
        """ prints with the `GS v 0`-command """
        width = int((im.width + 7) / 8)

        raster_send = b'\x1d\x76\x30\x00'
        max_slice_height = 255

        raster_data = b''
        dots = im.tobytes()
        while len(dots):
            im_slice = dots[:width*max_slice_height]
            slice_height = int(len(im_slice) / width)
            raster_data += raster_send + width.to_bytes(2, 'little') + slice_height.to_bytes(2, 'little') + im_slice
            dots = dots[width*max_slice_height:]

        return raster_data

    def extract_columns_from_picture(self, im, line_height):
        # Code inspired from python esc pos library:
        # https://github.com/python-escpos/python-escpos/blob/4a0f5855ef118a2009b843a3a106874701d8eddf/src/escpos/image.py#L73-L89
        width_pixels, height_pixels = im.size
        for left in range(0, width_pixels, line_height):
            box = (left, 0, left + line_height, height_pixels)
            im_chunk = im.transform(
                (line_height, height_pixels),
                Image.EXTENT,
                box
            )
            yield im_chunk.tobytes()

    def format_escpos_bit_image_column(self, im, high_density_vertical=True,
                                       high_density_horizontal=True,
                                       size_scale=100):
        """ prints with the `ESC *`-command
        reference: https://reference.epson-biz.com/modules/ref_escpos/index.php?content_id=88

        :param im: PIL image to print
        :param high_density_vertical: print in high density in vertical direction
        :param high_density_horizontal: print in high density in horizontal direction
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
        return raster_data

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

        if image_mode == 'column':
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
                        raise ValueError(
                            "Missing printer SCALE parameter integer "
                            "value in option: " + option)

            res = self.format_escpos_bit_image_column(im,
                                                      high_density_vertical,
                                                      high_density_horizontal,
                                                      scale)
        else:
            res = self.format_escpos_bit_image_raster(im)
        return res + RECEIPT_PRINTER_COMMANDS['escpos']['cut']

    def print_status(self):
        """Prints the status ticket of the IoTBox on the current printer."""
        wlan = ''
        ip = ''
        mac = ''
        homepage = ''
        pairing_code = ''

        ssid = helpers.get_ssid()
        wlan = '\nWireless network:\n%s\n\n' % ssid

        interfaces = ni.interfaces()
        ips = []
        for iface_id in interfaces:
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if conf.get('addr') and conf.get('addr'):
                    ips.append(conf.get('addr'))
        if len(ips) == 0:
            ip = '\nERROR: Could not connect to LAN\n\nPlease check that the IoTBox is correc-\ntly connected with a network cable,\n that the LAN is setup with DHCP, and\nthat network addresses are available'
        elif len(ips) == 1:
            ip = '\nIP Address:\n%s\n' % ips[0]
        else:
            ip = '\nIP Addresses:\n%s\n' % '\n'.join(ips)

        if len(ips) >= 1:
            ips_filtered = [i for i in ips if i != '127.0.0.1']
            main_ips = ips_filtered and ips_filtered[0] or '127.0.0.1'
            mac = '\nMAC Address:\n%s\n' % helpers.get_mac_address()
            homepage = '\nHomepage:\nhttp://%s:8069\n\n' % main_ips

        code = connection_manager.pairing_code
        if code:
            pairing_code = '\nPairing Code:\n%s\n' % code

        commands = RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
        title = commands['title'] % b'IoTBox Status'
        self.print_raw(commands['center'] + title + b'\n' + wlan.encode() + mac.encode() + ip.encode() + homepage.encode() + pairing_code.encode() + commands['cut'])

    def open_cashbox(self, data):
        """Sends a signal to the current printer to open the connected cashbox."""
        commands = RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
        for drawer in commands['drawers']:
            self.print_raw(drawer)

    def _action_default(self, data):
        self.print_raw(b64decode(data['document']))


class PrinterController(http.Controller):

    @http.route('/hw_proxy/default_printer_action', type='json', auth='none', cors='*')
    def default_printer_action(self, data):
        printer = next((d for d in iot_devices if iot_devices[d].device_type == 'printer' and iot_devices[d].device_connection == 'direct'), None)
        if printer:
            iot_devices[printer].action(data)
            return True
        return False


proxy_drivers['printer'] = PrinterDriver
