# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from threading import Thread
import time

from odoo.addons.hw_drivers.main import drivers, interfaces, iot_devices, unsupported_devices

_logger = logging.getLogger(__name__)


class Interface(Thread):
    _loop_delay = 3  # Delay (in seconds) between calls to get_devices or 0 if it should be called only once
    connection_type = ''
    allow_unsupported = False

    def __init__(self):
        super().__init__(daemon=True)
        self._detected_devices = set()
        self.drivers = sorted([d for d in drivers if d.connection_type == self.connection_type], key=lambda d: d.priority, reverse=True)

    def __init_subclass__(cls):
        super().__init_subclass__()
        interfaces[cls.__name__] = cls

    def run(self):
        while self.connection_type and self.drivers:
            self.update_iot_devices(self.get_devices())
            if not self._loop_delay:
                break
            time.sleep(self._loop_delay)

    def update_iot_devices(self, devices=None):
        if devices is None:
            devices = {}

        added = devices.keys() - self._detected_devices
        removed = self._detected_devices - devices.keys()
        self._detected_devices = set(devices.keys())

        for identifier in removed:
            if identifier in iot_devices:
                iot_devices[identifier].disconnect()
                _logger.info('Device %s is now disconnected', identifier)
            elif self.allow_unsupported and identifier in unsupported_devices:
                del unsupported_devices[identifier]
                _logger.info('Unsupported device %s is now disconnected', identifier)

        for identifier in added:
            supported_driver = next(
                (driver for driver in self.drivers if driver.supported(devices[identifier])),
                None
            )
            if supported_driver:
                _logger.info('Device %s is now connected', identifier)
                d = supported_driver(identifier, devices[identifier])
                iot_devices[identifier] = d
                # Start the thread after creating the iot_devices entry so the
                # thread can assume the iot_devices entry will exist while it's
                # running, at least until the `disconnect` above gets triggered
                # when `removed` is not empty.
                d.start()
            elif self.allow_unsupported:
                _logger.info('Unsupported device %s is now connected', identifier)
                unsupported_devices[identifier] = {
                    'name': f'Unknown device ({self.connection_type})',
                    'identifier': identifier,
                    'type': 'unsupported',
                    'connection': 'direct' if self.connection_type == 'usb' else self.connection_type,
                }

    def get_devices(self):
        raise NotImplementedError()

    def start(self):
        try:
            super().start()
        except Exception:
            _logger.exception("Interface %s could not be started", str(self))
