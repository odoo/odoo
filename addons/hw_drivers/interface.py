# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from threading import Thread
import time

from odoo.addons.hw_drivers.main import drivers, interfaces, iot_devices

_logger = logging.getLogger(__name__)


class InterfaceMetaClass(type):
    def __new__(cls, clsname, bases, attrs):
        if clsname in interfaces:
            return interfaces[clsname]
        new_interface = super(InterfaceMetaClass, cls).__new__(cls, clsname, bases, attrs)
        interfaces[clsname] = new_interface
        return new_interface


class Interface(Thread, metaclass=InterfaceMetaClass):
    _loop_delay = 3  # Delay (in seconds) between calls to get_devices or 0 if it should be called only once
    _detected_devices = {}
    connection_type = ''

    def __init__(self):
        super(Interface, self).__init__()
        self.drivers = sorted([d for d in drivers if d.connection_type == self.connection_type], key=lambda d: d.priority, reverse=True)

    def run(self):
        while self.connection_type and self.drivers:
            self.update_iot_devices(self.get_devices())
            if not self._loop_delay:
                break
            time.sleep(self._loop_delay)

    def update_iot_devices(self, devices={}):
        added = devices.keys() - self._detected_devices
        removed = self._detected_devices - devices.keys()
        self._detected_devices = devices.keys()

        for identifier in removed:
            if identifier in iot_devices:
                iot_devices[identifier].disconnect()
                _logger.info('Device %s is now disconnected', identifier)

        for identifier in added:
            for driver in self.drivers:
                if driver.supported(devices[identifier]):
                    _logger.info('Device %s is now connected', identifier)
                    d = driver(identifier, devices[identifier])
                    d.daemon = True
                    d.start()
                    iot_devices[identifier] = d
                    break

    def get_devices(self):
        raise NotImplementedError()
