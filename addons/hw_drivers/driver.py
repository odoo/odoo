# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from threading import Thread, Event

from odoo.addons.hw_drivers.main import drivers, iot_devices
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)


class DriverMetaClass(type):
    priority = -1

    def __new__(cls, clsname, bases, attrs):
        newclass = super(DriverMetaClass, cls).__new__(cls, clsname, bases, attrs)
        newclass.priority += 1
        if clsname != 'Driver':
            drivers.append(newclass)
        return newclass


class Driver(Thread, metaclass=DriverMetaClass):
    """
    Hook to register the driver into the drivers list
    """
    connection_type = ''

    def __init__(self, identifier, device):
        super(Driver, self).__init__()
        self.dev = device
        self.device_identifier = identifier
        self.device_name = ''
        self.device_connection = ''
        self.device_type = ''
        self.device_manufacturer = ''
        self.data = {'value': ''}
        self._actions = {}
        self._stopped = Event()

        # Least Recently Used (LRU) Cache that will store the idempotent keys already seen.
        self._iot_idempotent_ids_cache = LRU(500)

    @classmethod
    def supported(cls, device):
        """
        On specific driver override this method to check if device is supported or not
        return True or False
        """
        return False

    def action(self, data):
        """Helper function that calls a specific action method on the device.

        :param dict data: the `_actions` key mapped to the action method we want to call
        """
        self._actions[data.get('action', '')](data)

    def disconnect(self):
        self._stopped.set()
        del iot_devices[self.device_identifier]

    def _check_idempotency(self, iot_idempotent_id=None, session_id="unknown", **_kwargs):
        """Some IoT requests for the same action might be received several times.
        To avoid duplicating the resulting actions, we check if the action was "recently" executed.
        If this is the case, we will simply ignore the action

        :param str iot_idempotent_id: the idempotent ID received from the controller
        :param session_id: the session ID of the current request
        :param dict _kwargs: only here to allow providing the whole websocket/longpolling received dict
        :return: the `session_id` of the same `iot_idempotent_id` if any. False otherwise,
        which means that it is the first time that the IoT box received the request with this ID
        """
        if not iot_idempotent_id:
            return False

        cache = self._iot_idempotent_ids_cache
        if iot_idempotent_id in cache:
            _logger.debug(
                "Ignored request from '%s' as iot_idempotent_id '%s' already received",
                iot_idempotent_id, cache[iot_idempotent_id]
            )
            return cache[iot_idempotent_id]
        cache[iot_idempotent_id] = session_id
        return False
