# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import serial
import time

from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.iot_handlers.drivers.serial_base_driver import SerialDriver, SerialProtocol, serial_connection

_logger = logging.getLogger(__name__)


SylvacSCalProProtocol = SerialProtocol(
    name='Sylvac S_Cal pro',
    baudrate=4800,
    bytesize=serial.SEVENBITS,
    stopbits=serial.STOPBITS_TWO,
    parity=serial.PARITY_EVEN,
    timeout=0.2,
    writeTimeout=0.2,
    measureRegexp=b'\\+|-\\d+\\.\\d+\r',
    statusRegexp=None,
    commandTerminator=b'\r',
    commandDelay=0.2,
    measureDelay=0.2,
    newMeasureDelay=0.2,
    measureCommand=b'?',
    emptyAnswerValid=False,
)


class SylvacSCalProDriver(SerialDriver):
    """Driver For Sylvac's USB calipers."""

    _protocol = SylvacSCalProProtocol

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'device'
        self._actions['read_once'] = self._action_read_once

    def _action_read_once(self, _data):
        """Make value available to the longpolling event route"""
        event_manager.device_changed(self)

    def _take_measure(self):
        """Asks the device for a new value, and pushes that value to the frontend."""

        with self._device_lock:
            self._connection.write(self._protocol.measureCommand + self._protocol.commandTerminator)
            measure = self._get_raw_response(self._connection)
            if measure and measure != self.data['value']:
                self.data['value'] = measure
                event_manager.device_changed(self)

    @staticmethod
    def _get_raw_response(connection):
        """Gets a raw, unparsed string containing the updated value of the device.

        :param connection: connection to the device's serial port
        :type connection: pyserial.Serial
        """

        TIMEOUT = 1
        answer = []
        t0 = time.time()
        while True:
            char = connection.read()
            if char:
                if ord(char) == 13:
                    return b''.join(answer[:-1]).decode('utf-8')
                answer.append(char)
                t0 = time.time()
            elif time.time() - t0 > TIMEOUT:
                return ""

    @classmethod
    def supported(cls, device):
        """Checks whether the device at path `device` is supported by the driver.

        :param device: path to the device
        :type device: str
        :return: whether the device is supported by the driver
        :rtype: bool
        """

        protocol = cls._protocol

        try:
            with serial_connection(device['identifier'], protocol, is_probing=True) as connection:
                connection.write(protocol.measureCommand + protocol.commandTerminator)
                time.sleep(protocol.commandDelay)
                measure = cls._get_raw_response(connection)
                float(measure)
                return True

        except (ValueError, TypeError, serial.serialutil.SerialTimeoutException):
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s', device, protocol.name)
        return False
