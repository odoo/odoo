# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from cups import IPPError, IPP_PRINTER_IDLE, IPP_PRINTER_PROCESSING, IPP_PRINTER_STOPPED
import dbus
import logging
import netifaces as ni
import os
import io
import base64
import re
import subprocess
import tempfile
from PIL import Image, ImageOps

from odoo import http, _
from odoo.addons.hw_drivers.controllers.driver import event_manager, Driver, PPDs, conn, printers, cups_lock, iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_proxy.controllers.main import drivers as old_drivers

try:
    from odoo.addons.hw_drivers.controllers.driver import cm
except:
    cm = None

_logger = logging.getLogger(__name__)

def print_star_error(deviceId):
    """We communicate with receipt printers using the ESCPOS protocol.
    By default, Star printers use the Star mode. This can be changed by
    modifying the position of the DIP-Switches at the bottom of the printer.
    """
    error_page = (
        "\x1B\x1D\x61\x01"                                      # Centering start
        "\x1B\x69\x01\x01Bad configuration\x1B\x69\x00\x00"     # Title, double size
        "\n\n--------------------\n\n"
        "\x1B\x1D\x61\x00"                                      # Centering Stop
        "Your printer is in Star line mode, but should\n"
        "use ESC/POS mode. You will not be able to print\n"
        "receipts without changing your configuration.\n\n"
        "For more details and instructions on how to\n"
        "configure your printer, please refer to:\n\n"
        "\x1B\x1D\x61\x01"                                      # Centering start
        "\x1B\x2D\x01"                                          # Underline start
        "http://www.odoo.com"  # TODO: Replace URL
        "\x0A\x0A"
        "\x1B\x2D\x00"                                          # Underline stop
        "\x1B\x1D\x61\x00"                                      # Centering stop
        "\x1B\x64\x02"                                          # Full Cut
    )
    process = subprocess.Popen(["lp", "-d", deviceId], stdin=subprocess.PIPE)
    process.communicate(error_page.encode("utf-8"))

def cups_notification_handler(message, uri, device_id, state, reason, accepting_jobs):
    if device_id in iot_devices:
        reason = reason if reason != 'none' else None
        state_value = {
            IPP_PRINTER_IDLE: 'connected',
            IPP_PRINTER_PROCESSING: 'processing',
            IPP_PRINTER_STOPPED: 'stopped'
        }
        iot_devices[device_id].update_status(state_value[state], message, reason)

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

    def __init__(self, device):
        super(PrinterDriver, self).__init__(device)
        self._device_type = 'printer'
        self._device_connection = self.dev['device-class'].lower()
        self._device_name = self.dev['device-make-and-model']
        self.state = {
            'status': 'connecting',
            'message': 'Connecting to printer',
            'reason': None,
        }
        self.send_status()
        if 'direct' in self._device_connection and 'CMD:ESC/POS;' in self.dev['device-id']:
            self.print_status()

    @classmethod
    def supported(cls, device):
        protocol = ['dnssd', 'lpd', 'socket']
        if any(x in device['url'] for x in protocol) and device['device-make-and-model'] != 'Unknown' or 'direct' in device['device-class']:
            model = cls.get_device_model(device)
            ppdFile = ''
            for ppd in PPDs:
                if model and model in PPDs[ppd]['ppd-product']:
                    ppdFile = ppd
                    break
            with cups_lock:
                if ppdFile:
                    conn.addPrinter(name=device['identifier'], ppdname=ppdFile, device=device['url'])
                else:
                    conn.addPrinter(name=device['identifier'], device=device['url'])
                if device['identifier'] not in printers:
                    conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
                    conn.enablePrinter(device['identifier'])
                    conn.acceptJobs(device['identifier'])
                    conn.setPrinterUsersAllowed(device['identifier'], ['all'])
                    conn.addPrinterOptionDefault(device['identifier'], "usb-no-reattach", "true")
                    conn.addPrinterOptionDefault(device['identifier'], "usb-unidir", "true")
                else:
                    device['device-make-and-model'] = printers[device['identifier']]['printer-info']
            if 'STR_T' in device['device-id']:
                # Star printers have either STR_T or ESP in their name depending on the protocol used.
                print_star_error(device['identifier'])
            else:
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
        return re.sub("[\(].*?[\)]", "", device_model).strip()

    @classmethod
    def get_status(cls):
        status = 'connected' if any(iot_devices[d].device_type == "printer" and iot_devices[d].device_connection == 'direct' for d in iot_devices) else 'disconnected'
        return {'status': status, 'messages': ''}

    @property
    def device_identifier(self):
        return self.dev['identifier']

    def action(self, data):
        if data.get('action') == 'cashbox':
            self.open_cashbox()
        elif data.get('action') == 'print_receipt':
            self.print_receipt(base64.b64decode(data['receipt']))
        else:
            self.print_raw(b64decode(data['document']))

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

    def print_receipt(self, receipt):
        im = Image.open(io.BytesIO(receipt))

        # Convert to greyscale then to black and white
        im = im.convert("L")
        im = ImageOps.invert(im)
        im = im.convert("1")

        '''ESC a n
            - ESC a: Select justification, in hex: "1B 61"
            - n: Justification:
                - 0: left
                - 1: center
                - 2: right
        '''
        center = b'\x1b\x61\x01'

        '''GS v0 m x y
            - GS v0: Print raster bit image, in hex: "1D 76 30"
            - m: Density mode:
                - 0: 180dpi x 180dpi
                - 1: 180dpi x 90dpi
                - 2: 90dpi x 180 dpi
                - 3: 90dpi x 90 dpi
            - x: Length in X direction, in bytes, represented as 2 bytes in little endian
                --> Must be <= 255
            - y: Length in Y direction, in dots, represented as 2 bytes in little endian
        '''
        width_pixels, height_pixels = im.size
        width_bytes = int((width_pixels + 7) / 8)
        print_command = b"\x1d\x76\x30" + b'\x00' + (width_bytes).to_bytes(2, 'little') + height_pixels.to_bytes(2, 'little')

        # There is a height limit when printing images, so we split the image
        # into slices and print each slice with a separate command.
        blobs = []
        slice_offset = 0
        while slice_offset < height_pixels:
            slice_height_pixels = min(255, height_pixels - slice_offset)
            im_slice = im.crop((0, slice_offset, width_pixels, slice_offset + slice_height_pixels))
            print_command = b"\x1d\x76\x30" + b'\x00' + (width_bytes).to_bytes(2, 'little') + slice_height_pixels.to_bytes(2, 'little')
            blobs += [print_command + im_slice.tobytes()]
            slice_offset += slice_height_pixels

        '''GS V m
            - GS V: Cut, in hex: "1D 56"
            - m: Cut mode:
                - 0: Full cut
                - 1: Partial cut
                - 65 (0x41): Feed paper then full cut
                - 66 (0x42): Feed paper then partial cut
        '''
        cut = b'\x1d\x56' + b'\x41'

        self.print_raw(center + b"".join(blobs) + cut + b'\n')

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

        code = cm and cm.pairing_code
        if code:
            pairing_code = '\nPairing Code:\n%s\n' % code

        center = b'\x1b\x61\x01'
        title = b'\n\x1b\x21\x30\x1b\x4d\x01IoTBox Status\x1b\x4d\x00\x1b\x21\x00\n'
        cut = b'\x1d\x56\x41'

        self.print_raw(center + title + wlan.encode() + mac.encode() + ip.encode() + homepage.encode() + pairing_code.encode() + cut + b'\n')

    def open_cashbox(self):
        """Sends a signal to the current printer to open the connected cashbox."""
        # ESC = --> Set peripheral device
        self.print_raw(b'\x1b\x3d\x01')
        for drawer in [b'\x1b\x70\x00', b'\x1b\x70\x01']:  # Kick pin 2 and 5
            command = drawer + b'\x19\x19'  # Pulse ON during 50ms then OFF during 50ms
            self.print_raw(command)


class PrinterController(http.Controller):

    @http.route('/hw_proxy/default_printer_action', type='json', auth='none', cors='*')
    def default_printer_action(self, data):
        printer = next((d for d in iot_devices if iot_devices[d].device_type == 'printer' and iot_devices[d].device_connection == 'direct'), None)
        if printer:
            iot_devices[printer].action(data)
            return True
        return False

old_drivers['printer'] = PrinterDriver
