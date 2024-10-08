# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import namedtuple
from contextlib import contextmanager
import logging
import serial
from threading import Lock
import time
import traceback

from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.driver import Driver

_logger = logging.getLogger(__name__)

SerialProtocol = namedtuple(
    'SerialProtocol',
    "name baudrate bytesize stopbits parity timeout writeTimeout measureRegexp statusRegexp "
    "commandTerminator commandDelay measureDelay newMeasureDelay "
    "measureCommand emptyAnswerValid")


@contextmanager
def serial_connection(path, protocol, is_probing=False):
    """Opens a serial connection to a device and closes it automatically after use.

    :param path: path to the device
    :type path: string
    :param protocol: an object containing the serial protocol to connect to a device
    :type protocol: namedtuple
    :param is_probing: a flag thet if set to `True` makes the timeouts longer, defaults to False
    :type is_probing: bool, optional
    """

    PROBING_TIMEOUT = 1
    port_config = {
        'baudrate': protocol.baudrate,
        'bytesize': protocol.bytesize,
        'stopbits': protocol.stopbits,
        'parity': protocol.parity,
        'timeout': PROBING_TIMEOUT if is_probing else protocol.timeout,               # longer timeouts for probing
        'writeTimeout': PROBING_TIMEOUT if is_probing else protocol.writeTimeout      # longer timeouts for probing
    }
    connection = serial.Serial(path, **port_config)
    yield connection
    connection.close()


class SerialDriver(Driver):
    """Abstract base class for serial drivers."""

    _protocol = None
    connection_type = 'serial'

    STATUS_CONNECTED = 'connected'
    STATUS_ERROR = 'error'
    STATUS_CONNECTING = 'connecting'
    STATUS_DISCONNECTED = 'disconnected'

    def __init__(self, identifier, device):
        """ Attributes initialization method for `SerialDriver`.

        :param device: path to the device
        :type device: str
        """

        super(SerialDriver, self).__init__(identifier, device)
        self._actions.update({
            'get_status': self._push_status,
        })
        self.device_connection = 'serial'
        self._device_lock = Lock()
        self._status = {'status': self.STATUS_CONNECTING, 'message_title': '', 'message_body': ''}
        self._set_name()

    def _get_raw_response(connection):
        pass

    def _push_status(self):
        """Updates the current status and pushes it to the frontend."""

        self.data['status'] = self._status
        event_manager.device_changed(self)

    def _set_name(self):
        """Tries to build the device's name based on its type and protocol name but falls back on a default name if that doesn't work."""

        try:
            name = ('%s serial %s' % (self._protocol.name, self.device_type)).title()
        except Exception:
            name = 'Unknown Serial Device'
        self.device_name = name

    def _take_measure(self):
        pass

    def _do_action(self, data):
        """Helper function that calls a specific action method on the device.

        :param data: the `_actions` key mapped to the action method we want to call
        :type data: string
        """

        try:
            with self._device_lock:
                self._actions[data['action']](data)
                time.sleep(self._protocol.commandDelay)
        except Exception:
            msg = 'An error occurred while performing action %s on %s' % (data, self.device_name)
            _logger.exception(msg)
            self._status = {'status': self.STATUS_ERROR, 'message_title': msg, 'message_body': traceback.format_exc()}
            self._push_status()

    def action(self, data):
        """Establish a connection with the device if needed and have it perform a specific action.

        :param data: the `_actions` key mapped to the action method we want to call
        :type data: string
        """

        if self._connection and self._connection.isOpen():
            self._do_action(data)
        else:
            with serial_connection(self.device_identifier, self._protocol) as connection:
                self._connection = connection
                self._do_action(data)

    def run(self):
        """Continuously gets new measures from the device."""

        try:
            with serial_connection(self.device_identifier, self._protocol) as connection:
                self._connection = connection
                self._status['status'] = self.STATUS_CONNECTED
                self._push_status()
                while not self._stopped.is_set():
                    self._take_measure()
                    time.sleep(self._protocol.newMeasureDelay)
                self._status['status'] = self.STATUS_DISCONNECTED
                self._push_status()
        except Exception:
            msg = 'Error while reading %s' % self.device_name
            _logger.exception(msg)
            self._status = {'status': self.STATUS_ERROR, 'message_title': msg, 'message_body': traceback.format_exc()}
            self._push_status()
