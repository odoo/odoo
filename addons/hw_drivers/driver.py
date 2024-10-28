# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from threading import Thread, Event

from odoo.addons.hw_drivers.main import drivers, iot_devices
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.tools.helpers import toggleable

from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)


class Driver(Thread):
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

    def __init_subclass__(cls):
        super().__init_subclass__()
        if hasattr(cls, 'priority'):
            cls.priority += 1
        else:
            cls.priority = 0
        drivers.append(cls)

    @classmethod
    def supported(cls, device):
        """
        On specific driver override this method to check if device is supported or not
        return True or False
        """
        return False

    @toggleable
    def action(self, action='', **kwargs):
        """Helper function that calls a specific action method on the device.

        :param str action: the action to be executed
        :param dict kwargs: the parameters to be passed to the action method
        :return: the result of the action method
        """
        try:
            response = {'status': 'success', 'result': self._actions[action](**kwargs), 'action_args': {**kwargs}}
        except Exception as e:
            _logger.exception("Error while executing action %s with params %s", action, kwargs)
            response = {'status': 'error', 'result': str(e), 'action_args': {**kwargs}}

        event_manager.device_changed(self, response)  # Make response available to /event route or websocket

    def disconnect(self):
        self._stopped.set()
        del iot_devices[self.device_identifier]

    def is_idempotent(self, session_id, **kwargs):
        """Some IoT requests for the same action might be received several times.
        To avoid duplicating the resulting actions, we check if the action was "recently" executed.
        If this is the case, we will simply ignore the action

        :param str session_id: the session id of the request
        :param dict kwargs: params passed to the action method
        :return: True if the action is idempotent, False otherwise
        :rtype: bool
        """
        idempotent_id = kwargs.get("iot_idempotent_id")
        if not idempotent_id or not session_id:
            return True
        if idempotent_id not in self._iot_idempotent_ids_cache:
            self._iot_idempotent_ids_cache[idempotent_id] = session_id
            return True

        _logger.info(
            "Action from %s with idempotent Id %s already received from session %s",
            session_id, idempotent_id, self._iot_idempotent_ids_cache[idempotent_id]
        )
        return False
