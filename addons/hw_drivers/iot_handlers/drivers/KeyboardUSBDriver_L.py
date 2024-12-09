# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import evdev
import json
import logging
from lxml import etree
import os
from pathlib import Path
from queue import Queue, Empty
import re
import requests
import subprocess
from threading import Lock
import time
from usb import util

from odoo import http
from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)
xlib = ctypes.cdll.LoadLibrary('libX11.so.6')


class KeyboardUSBDriver(Driver):
    connection_type = 'usb'
    keyboard_layout_groups = []
    available_layouts = []

    def __init__(self, identifier, device):
        if not hasattr(KeyboardUSBDriver, 'display'):
            os.environ['XAUTHORITY'] = "/run/lightdm/pi/xauthority"
            KeyboardUSBDriver.display = xlib.XOpenDisplay(bytes(":0.0", "utf-8"))

        super(KeyboardUSBDriver, self).__init__(identifier, device)
        self.device_connection = 'direct'
        self.device_name = self._set_name()

        self._actions.update({
            'update_layout': self._update_layout,
            'update_is_scanner': self._save_is_scanner,
            '': self._action_default,
        })

        # from https://github.com/xkbcommon/libxkbcommon/blob/master/test/evdev-scancodes.h
        self._scancode_to_modifier = {
            42: 'left_shift',
            54: 'right_shift',
            58: 'caps_lock',
            69: 'num_lock',
            100: 'alt_gr', # right alt
        }
        self._tracked_modifiers = {modifier: False for modifier in self._scancode_to_modifier.values()}

        if not KeyboardUSBDriver.available_layouts:
            KeyboardUSBDriver.load_layouts_list()
        KeyboardUSBDriver.send_layouts_list()

        for evdev_device in [evdev.InputDevice(path) for path in evdev.list_devices()]:
            if (device.idVendor == evdev_device.info.vendor) and (device.idProduct == evdev_device.info.product):
                self.input_device = evdev_device

        self._set_device_type('scanner') if self._is_scanner() else self._set_device_type()

    @classmethod
    def supported(cls, device):
        for cfg in device:
            for itf in cfg:
                if itf.bInterfaceClass == 3 and itf.bInterfaceProtocol != 2:
                    device.interface_protocol = itf.bInterfaceProtocol
                    return True
        return False

    @classmethod
    def get_status(self):
        """Allows `hw_proxy.Proxy` to retrieve the status of the scanners"""
        status = 'connected' if any(iot_devices[d].device_type == "scanner" for d in iot_devices) else 'disconnected'
        return {'status': status, 'messages': ''}

    @classmethod
    @helpers.require_db
    def send_layouts_list(cls):
        server = helpers.get_odoo_server_url() + '/iot/keyboard_layouts'
        try:
            response = requests.post(
                server, data={'available_layouts': json.dumps(cls.available_layouts)}, timeout=5
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.exception('Could not reach configured server to send available layouts')

    @classmethod
    def load_layouts_list(cls):
        tree = etree.parse("/usr/share/X11/xkb/rules/base.xml", etree.XMLParser(ns_clean=True, recover=True))
        layouts = tree.xpath("//layout")
        for layout in layouts:
            layout_name = layout.xpath("./configItem/name")[0].text
            layout_description = layout.xpath("./configItem/description")[0].text
            KeyboardUSBDriver.available_layouts.append({
                'name': layout_description,
                'layout': layout_name,
            })
            for variant in layout.xpath("./variantList/variant"):
                variant_name = variant.xpath("./configItem/name")[0].text
                variant_description = variant.xpath("./configItem/description")[0].text
                KeyboardUSBDriver.available_layouts.append({
                    'name': variant_description,
                    'layout': layout_name,
                    'variant': variant_name,
                })

    def _set_name(self):
        try:
            manufacturer = util.get_string(self.dev, self.dev.iManufacturer)
            product = util.get_string(self.dev, self.dev.iProduct)
            return re.sub(r"[^\w \-+/*&]", '', "%s - %s" % (manufacturer, product))
        except ValueError as e:
            _logger.warning(e)
            return 'Unknown input device'

    def run(self):
        try:
            for event in self.input_device.read_loop():
                if self._stopped.is_set():
                    break
                if event.type == evdev.ecodes.EV_KEY:
                    data = evdev.categorize(event)

                    modifier_name = self._scancode_to_modifier.get(data.scancode)
                    if modifier_name:
                        if modifier_name in ('caps_lock', 'num_lock'):
                            if data.keystate == 1:
                                self._tracked_modifiers[modifier_name] = not self._tracked_modifiers[modifier_name]
                        else:
                            self._tracked_modifiers[modifier_name] = bool(data.keystate)  # 1 for keydown, 0 for keyup
                    elif data.keystate == 1:
                        self.key_input(data.scancode)

        except Exception as err:
            _logger.warning(err)

    def _change_keyboard_layout(self, new_layout):
        """Change the layout of the current device to what is specified in
        new_layout.

        Args:
            new_layout (dict): A dict containing two keys:
                - layout (str): The layout code
                - variant (str): An optional key to represent the variant of the
                                 selected layout
        """
        if hasattr(self, 'keyboard_layout'):
            KeyboardUSBDriver.keyboard_layout_groups.remove(self.keyboard_layout)

        if new_layout:
            self.keyboard_layout = new_layout.get('layout') or 'us'
            if new_layout.get('variant'):
                self.keyboard_layout += "(%s)" % new_layout['variant']
        else:
            self.keyboard_layout = 'us'

        KeyboardUSBDriver.keyboard_layout_groups.append(self.keyboard_layout)
        subprocess.call(["setxkbmap", "-display", ":0.0", ",".join(KeyboardUSBDriver.keyboard_layout_groups)])

        # Close then re-open display to refresh the mapping
        xlib.XCloseDisplay(KeyboardUSBDriver.display)
        KeyboardUSBDriver.display = xlib.XOpenDisplay(bytes(":0.0", "utf-8"))

    def save_layout(self, layout):
        """Save the layout to a file on the box to read it when restarting it.
        We need that in order to keep the selected layout after a reboot.

        Args:
            new_layout (dict): A dict containing two keys:
                - layout (str): The layout code
                - variant (str): An optional key to represent the variant of the
                                 selected layout
        """
        file_path = helpers.path_file('odoo-keyboard-layouts.conf')
        if file_path.exists():
            data = json.loads(file_path.read_text())
        else:
            data = {}
        data[self.device_identifier] = layout
        helpers.write_file('odoo-keyboard-layouts.conf', json.dumps(data))

    def load_layout(self):
        """Read the layout from the saved filed and set it as current layout.
        If no file or no layout is found we use 'us' by default.
        """
        file_path = helpers.path_file('odoo-keyboard-layouts.conf')
        if file_path.exists():
            data = json.loads(file_path.read_text())
            layout = data.get(self.device_identifier, {'layout': 'us'})
        else:
            layout = {'layout': 'us'}
        self._change_keyboard_layout(layout)

    def _action_default(self, data):
        self.data['value'] = ''
        event_manager.device_changed(self)

    def _is_scanner(self):
        """Read the device type from the saved filed and set it as current type.
        If no file or no device type is found we try to detect it automatically.
        """
        device_name = self.device_name.lower()
        scanner_name = ['barcode', 'scanner', 'reader']
        is_scanner = any(x in device_name for x in scanner_name) or self.dev.interface_protocol == '0'

        file_path = helpers.path_file('odoo-keyboard-is-scanner.conf')
        if file_path.exists():
            data = json.loads(file_path.read_text())
            is_scanner = data.get(self.device_identifier, {}).get('is_scanner', is_scanner)
        return is_scanner

    def _keyboard_input(self, scancode):
        """Deal with a keyboard input. Send the character corresponding to the
        pressed key represented by its scancode to the connected Odoo instance.

        Args:
            scancode (int): The scancode of the pressed key.
        """
        self.data['value'] = self._scancode_to_char(scancode)
        if self.data['value']:
            event_manager.device_changed(self)

    def _barcode_scanner_input(self, scancode):
        """Deal with a barcode scanner input. Add the new character scanned to
        the current barcode or complete the barcode if "Return" is pressed.
        When a barcode is completed, two tasks are performed:
            - Send a device_changed update to the event manager to notify the
            listeners that the value has changed (used in Enterprise).
            - Add the barcode to the list barcodes that are being queried in
            Community.

        Args:
            scancode (int): The scancode of the pressed key.
        """
        if scancode == 28:  # Return
            self.data['value'] = self._current_barcode
            event_manager.device_changed(self)
            self._barcodes.put((time.time(), self._current_barcode))
            self._current_barcode = ''
        else:
            self._current_barcode += self._scancode_to_char(scancode)

    def _save_is_scanner(self, data):
        """Save the type of device.
        We need that in order to keep the selected type of device after a reboot.
        """
        is_scanner = {'is_scanner': data.get('is_scanner')}
        file_path = helpers.path_file('odoo-keyboard-is-scanner.conf')
        if file_path.exists():
            data = json.loads(file_path.read_text())
        else:
            data = {}
        data[self.device_identifier] = is_scanner
        helpers.write_file('odoo-keyboard-is-scanner.conf', json.dumps(data))
        self._set_device_type('scanner') if is_scanner.get('is_scanner') else self._set_device_type()

    def _update_layout(self, data):
        layout = {
            'layout': data.get('layout'),
            'variant': data.get('variant'),
        }
        self._change_keyboard_layout(layout)
        self.save_layout(layout)

    def _set_device_type(self, device_type='keyboard'):
        """Modify the device type between 'keyboard' and 'scanner'

        Args:
            type (string): Type wanted to switch
        """
        if device_type == 'scanner':
            self.device_type = 'scanner'
            self.key_input = self._barcode_scanner_input
            self._barcodes = Queue()
            self._current_barcode = ''
            self.input_device.grab()
            self.read_barcode_lock = Lock()
        else:
            self.device_type = 'keyboard'
            self.key_input = self._keyboard_input
        self.load_layout()

    def _scancode_to_char(self, scancode):
        """Translate a received scancode to a character depending on the
        selected keyboard layout and the current state of the keyboard's
        modifiers.

        Args:
            scancode (int): The scancode of the pressed key, to be translated to
                a character

        Returns:
            str: The translated scancode.
        """
        # Scancode -> Keysym : Depends on the keyboard layout
        group = KeyboardUSBDriver.keyboard_layout_groups.index(self.keyboard_layout)
        modifiers = self._get_active_modifiers(scancode)
        keysym = ctypes.c_int(xlib.XkbKeycodeToKeysym(KeyboardUSBDriver.display, scancode + 8, group, modifiers))

        # Translate Keysym to a character
        key_pressed = ctypes.create_string_buffer(5)
        xlib.XkbTranslateKeySym(KeyboardUSBDriver.display, ctypes.byref(keysym), 0, ctypes.byref(key_pressed), 5, ctypes.byref(ctypes.c_int()))
        if key_pressed.value:
            return key_pressed.value.decode('utf-8')
        return ''

    def _get_active_modifiers(self, scancode):
        """Get the state of currently active modifiers.

        Args:
            scancode (int): The scancode of the key being translated

        Returns:
            int: The current state of the modifiers:
                0 -- Lowercase
                1 -- Highercase or (NumLock + key pressed on keypad)
                2 -- AltGr
                3 -- Highercase + AltGr
        """
        modifiers = 0
        uppercase = (self._tracked_modifiers['right_shift'] or self._tracked_modifiers['left_shift']) ^ self._tracked_modifiers['caps_lock']
        if uppercase or (scancode in [71, 72, 73, 75, 76, 77, 79, 80, 81, 82, 83] and self._tracked_modifiers['num_lock']):
            modifiers += 1

        if self._tracked_modifiers['alt_gr']:
            modifiers += 2

        return modifiers

    def read_next_barcode(self):
        """Get the value of the last barcode that was scanned but not sent yet
        and not older than 5 seconds. This function is used in Community, when
        we don't have access to the IoTLongpolling.

        Returns:
            str: The next barcode to be read or an empty string.
        """

        # Previous query still running, stop it by sending a fake barcode
        if self.read_barcode_lock.locked():
            self._barcodes.put((time.time(), ""))

        with self.read_barcode_lock:
            try:
                timestamp, barcode = self._barcodes.get(True, 55)
                if timestamp > time.time() - 5:
                    return barcode
            except Empty:
                return ''

proxy_drivers['scanner'] = KeyboardUSBDriver


class KeyboardUSBController(http.Controller):
    @http.route('/hw_proxy/scanner', type='jsonrpc', auth='none', cors='*')
    def get_barcode(self):
        scanners = [iot_devices[d] for d in iot_devices if iot_devices[d].device_type == "scanner"]
        if scanners:
            return scanners[0].read_next_barcode()
        time.sleep(5)
        return None
