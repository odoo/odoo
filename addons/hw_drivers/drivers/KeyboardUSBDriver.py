# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import evdev
import logging
from usb import util

from odoo import _
from odoo.addons.hw_drivers.controllers.driver import event_manager, Driver

_logger = logging.getLogger(__name__)


class KeyboardUSBDriver(Driver):
    connection_type = 'usb'

    def __init__(self, device):
        super(KeyboardUSBDriver, self).__init__(device)
        self._device_type = 'device'
        self._device_connection = 'direct'
        self._device_name = self._get_name()

    @classmethod
    def supported(cls, device):
        for cfg in device:
            for itf in cfg:
                if itf.bInterfaceClass == 3 and itf.bInterfaceProtocol == 1:
                    return True
        return False

    def _get_name(self):
        try:
            manufacturer = util.get_string(self.dev, 256, self.dev.iManufacturer)
            product = util.get_string(self.dev, 256, self.dev.iProduct)
            return ("%s - %s") % (manufacturer, product)
        except ValueError as e:
            _logger.warning(e)
            return _('Unknow keyboard')

    def action(self, data):
        self.data['value'] = ''
        event_manager.device_changed(self)

    def run(self):
        devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for device in devices:
            if (self.dev.idVendor == device.info.vendor) and (self.dev.idProduct == device.info.product):
                path = device.path
        device = evdev.InputDevice(path)

        try:
            for event in device.read_loop():
                if event.type == evdev.ecodes.EV_KEY:
                    data = evdev.categorize(event)
                    if data.keystate:
                        self.data['value'] = data.keycode.replace('KEY_','')
                        event_manager.device_changed(self)
        except Exception as err:
            _logger.warning(err)
