# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from threading import Thread, Event

from odoo.addons.iot_drivers.main import drivers, iot_devices
from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.tools.helpers import toggleable
from odoo.tools.lru import LRU

_logger = logging.getLogger(__name__)


class Driver(Thread):
    """Hook to register the driver into the drivers list"""
    connection_type = ''
    priority = 0

    def __init__(self, identifier, device):
        super().__init__(daemon=True)
        self.dev = device
        self.device_identifier = identifier
        self.device_name = ''
        self.device_connection = ''
        self.device_type = ''
        self.device_manufacturer = ''
        self.data = {'value': '', 'result': ''}  # TODO: deprecate "value"?
        self._actions = {}
        self._stopped = Event()
        self._recent_action_ids = LRU(256)

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls not in drivers:
            drivers.append(cls)

    @classmethod
    def supported(cls, device):
        """
        On specific driver override this method to check if device is supported or not
        return True or False
        """
        return False

    @toggleable
    def action(self, data):
        """Helper function that calls a specific action method on the device.

        :param dict data: the action method name and the parameters to be passed to it
        :return: the result of the action method
        """
        action = data.get('action', '')
        action_unique_id = data.get('action_unique_id')
        if action_unique_id:
            if action_unique_id in self._recent_action_ids:
                _logger.warning("Duplicate action %s id %s received, ignoring", action, action_unique_id)
                return
            self._recent_action_ids[action_unique_id] = action_unique_id

        session_id = data.get('session_id')
        if session_id:
            self.data["owner"] = session_id
            self.data["session_id"] = session_id

        base_response = {'action_args': {**data}, 'session_id': data.get('session_id')}
        try:
            response = {'status': 'success', 'result': self._actions[action](data), **base_response}
        except Exception as e:
            if action_unique_id:
                self._recent_action_ids.pop(action_unique_id, None)
            _logger.exception("Error while executing action %s with params %s", action, data)
            response = {'status': 'error', 'result': str(e), **base_response}

        # Make response available to /event route or websocket
        # printers and payment terminals handle their own events (low on paper, waiting for card, etc.)
        if self.device_type not in ["printer", "payment"]:
            event_manager.device_changed(self, response)

    def disconnect(self):
        self._stopped.set()
        del iot_devices[self.device_identifier]
