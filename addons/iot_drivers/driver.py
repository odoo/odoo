# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from threading import Thread, Event

from odoo.addons.iot_drivers.main import drivers, iot_devices
from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.tools.helpers import toggleable

_logger = logging.getLogger(__name__)


class Driver(Thread):
    """Hook to register the driver into the drivers list"""
    connection_type = ''
    daemon = True
    priority = 0

    def __init__(self, identifier, device):
        super().__init__()
        self.dev = device
        self.device_identifier = identifier
        self.device_name = ''
        self.device_connection = ''
        self.device_type = ''
        self.device_manufacturer = ''
        self.data = {'value': ''}
        self._actions = {}
        self._stopped = Event()

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
        try:
            response = {'status': 'success', 'result': self._actions[action](data), 'action_args': {**data}}
        except Exception as e:
            _logger.exception("Error while executing action %s with params %s", action, data)
            response = {'status': 'error', 'result': str(e), 'action_args': {**data}}

        # Make response available to /event route or websocket
        # printers handle their own events (low on paper, etc.)
        if self.device_type != "printer":
            event_manager.device_changed(self, response)

    def disconnect(self):
        self._stopped.set()
        del iot_devices[self.device_identifier]
