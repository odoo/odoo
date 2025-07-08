# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import serial
import threading
import time

from odoo import http
from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.iot_handlers.drivers.SerialBaseDriver import SerialDriver, SerialProtocol, serial_connection


_logger = logging.getLogger(__name__)

# Only needed to expose scale via hw_proxy (used by Community edition)
ACTIVE_SCALE = None
new_weight_event = threading.Event()

# 8217 Mettler-Toledo (Weight-only) Protocol, as described in the scale's Service Manual.
#    e.g. here: https://www.manualslib.com/manual/861274/Mettler-Toledo-Viva.html?page=51#manual
# Our recommended scale, the Mettler-Toledo "Ariva-S", supports this protocol on
# both the USB and RS232 ports, it can be configured in the setup menu as protocol option 3.
# We use the default serial protocol settings, the scale's settings can be configured in the
# scale's menu anyway.
Toledo8217Protocol = SerialProtocol(
    name='Toledo 8217',
    baudrate=9600,
    bytesize=serial.SEVENBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_EVEN,
    timeout=1,
    writeTimeout=1,
    measureRegexp=b"\x02\\s*([0-9.]+)N?\\r",
    statusRegexp=b"\x02\\s*\\?([^\x00])\\r",
    commandDelay=0.2,
    measureDelay=0.5,
    newMeasureDelay=0.2,
    commandTerminator=b'',
    measureCommand=b'W',
    emptyAnswerValid=False,
)

# The ADAM scales have their own RS232 protocol, usually documented in the scale's manual
#   e.g at https://www.adamequipment.com/media/docs/Print%20Publications/Manuals/PDF/AZEXTRA/AZEXTRA-UM.pdf
#          https://www.manualslib.com/manual/879782/Adam-Equipment-Cbd-4.html?page=32#manual
# Only the baudrate and label format seem to be configurable in the AZExtra series.
ADAMEquipmentProtocol = SerialProtocol(
    name='Adam Equipment',
    baudrate=4800,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=0.2,
    writeTimeout=0.2,
    measureRegexp=rb"\s*([0-9.]+)kg",  # LABEL format 3 + KG in the scale settings, but Label 1/2 should work
    statusRegexp=None,
    commandTerminator=b"\r\n",
    commandDelay=0.2,
    measureDelay=0.5,
    # AZExtra beeps every time you ask for a weight that was previously returned!
    # Adding an extra delay gives the operator a chance to remove the products
    # before the scale starts beeping. Could not find a way to disable the beeps.
    newMeasureDelay=5,
    measureCommand=b'P',
    emptyAnswerValid=True,  # AZExtra does not answer unless a new non-zero weight has been detected
)


# HW Proxy is used by Community edition
class ScaleReadHardwareProxy(http.Controller):
    @http.route('/hw_proxy/scale_read', type='json', auth='none', cors='*')
    def scale_read(self):
        if ACTIVE_SCALE:
            return {'weight': ACTIVE_SCALE._scale_read_hw_proxy()}
        return None


class ScaleDriver(SerialDriver):
    """Abstract base class for scale drivers."""
    last_sent_value = None

    def __init__(self, identifier, device):
        super(ScaleDriver, self).__init__(identifier, device)
        self.device_type = 'scale'
        self._set_actions()
        self._is_reading = True

        # The HW Proxy can only expose one scale,
        # only the last scale connected is kept
        global ACTIVE_SCALE
        ACTIVE_SCALE = self
        proxy_drivers['scale'] = ACTIVE_SCALE

    # Used by the HW Proxy in Community edition
    def get_status(self):
        """Allows `hw_proxy.Proxy` to retrieve the status of the scales"""

        status = self._status
        return {'status': status['status'], 'messages': [status['message_title'], ]}

    def _set_actions(self):
        """Initializes `self._actions`, a map of action keys sent by the frontend to backend action methods."""

        self._actions.update({
            'read_once': self._read_once_action,
            'start_reading': self._start_reading_action,
            'stop_reading': self._stop_reading_action,
        })

    def _start_reading_action(self, data):
        """Starts asking for the scale value."""
        self._is_reading = True

    def _stop_reading_action(self, data):
        """Stops asking for the scale value."""
        self._is_reading = False

    def _read_once_action(self, data):
        """Reads the scale current weight value and pushes it to the frontend."""

        self._read_weight()
        self.last_sent_value = self.data['value']
        event_manager.device_changed(self)

    @staticmethod
    def _get_raw_response(connection):
        """Gets raw bytes containing the updated value of the device.

        :param connection: a connection to the device's serial port
        :type connection: pyserial.Serial
        :return: the raw response to a weight request
        :rtype: str
        """

        answer = []
        while True:
            char = connection.read(1)
            if not char:
                break
            else:
                answer.append(bytes(char))
        return b''.join(answer)

    def _read_weight(self):
        """Asks for a new weight from the scale, checks if it is valid and, if it is, makes it the current value."""

        protocol = self._protocol
        self._connection.write(protocol.measureCommand + protocol.commandTerminator)
        answer = self._get_raw_response(self._connection)
        match = re.search(self._protocol.measureRegexp, answer)
        if match:
            self.data = {
                'value': float(match.group(1)),
                'status': self._status
            }
        else:
            self._read_status(answer)

    # Ensures compatibility with Community edition
    def _scale_read_hw_proxy(self):
        """Used when the iot app is not installed"""
        with self._device_lock:
            self._read_weight()
        return self.data['value']

    def _take_measure(self):
        """Reads the device's weight value, and pushes that value to the frontend."""

        with self._device_lock:
            self._read_weight()
            if self.data['value'] != self.last_sent_value or self._status['status'] == self.STATUS_ERROR:
                self.last_sent_value = self.data['value']
                event_manager.device_changed(self)


class Toledo8217Driver(ScaleDriver):
    """Driver for the Toldedo 8217 serial scale."""
    _protocol = Toledo8217Protocol

    def __init__(self, identifier, device):
        super(Toledo8217Driver, self).__init__(identifier, device)
        self.device_manufacturer = 'Toledo'

    @classmethod
    def supported(cls, device):
        """Checks whether the device, which port info is passed as argument, is supported by the driver.

        :param device: path to the device
        :type device: str
        :return: whether the device is supported by the driver
        :rtype: bool
        """

        protocol = cls._protocol

        try:
            with serial_connection(device['identifier'], protocol, is_probing=True) as connection:
                connection.write(b'Ehello' + protocol.commandTerminator)
                time.sleep(protocol.commandDelay)
                answer = connection.read(8)
                if answer == b'\x02E\rhello':
                    connection.write(b'F' + protocol.commandTerminator)
                    return True
        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s' % (device, protocol.name))
        return False

    def _read_status(self, answer):
        """
        Status byte in form of an ascii character (Ex: 'D') is sent if scale is in motion, or is net/gross weight is negative or over capacity.
        Convert the status byte to a binary string, and check its bits to see if there is an error.
        LSB is the last char so the binary string is read in reverse and the first char is a parity bit, so we ignore it.
        :param answer: scale answer (Example: b'\x02?D\r')
        :type answer: bytestring
        """
        status_char_error_bits = (
            'Scale in motion',  # 0
            'Over capacity',  # 1
            'Under zero',  # 2
            'Outside zero capture range',  # 3
            'Center of zero',  # 4
            'Net weight',  # 5
            'Bad Command from host',  # 6
        )

        status_match = self._protocol.statusRegexp and re.search(self._protocol.statusRegexp, answer)
        if status_match:
            status_char = status_match.group(1).decode()  # Example: b'D' extracted from b'\x02?D\r'
            binary_status_char = format(ord(status_char), '08b')  # Example: '00001101'
            for index, bit in enumerate(binary_status_char[1:][::-1]):  # Read the bits in reverse order (LSB is at the last char) + ignore the first "parity" bit
                if int(bit):
                    _logger.debug("Scale error: %s. Status string: %s. Scale answer: %s.", status_char_error_bits[index], binary_status_char, answer)
                    self.data = {
                        'value': 0,
                        'status': self._status,
                    }
                    break


class AdamEquipmentDriver(ScaleDriver):
    """Driver for the Adam Equipment serial scale."""

    _protocol = ADAMEquipmentProtocol
    priority = 0  # Test the supported method of this driver last, after all other serial drivers

    def __init__(self, identifier, device):
        super(AdamEquipmentDriver, self).__init__(identifier, device)
        self._is_reading = False
        self._last_weight_time = 0
        self.device_manufacturer = 'Adam'

    def _check_last_weight_time(self):
        """The ADAM doesn't make the difference between a value of 0 and "the same value as last time":
        in both cases it returns an empty string.
        With this, unless the weight changes, we give the user `TIME_WEIGHT_KEPT` seconds to log the new weight,
        then change it back to zero to avoid keeping it indefinetely, which could cause issues.
        In any case the ADAM must always go back to zero before it can weight again.
        """

        TIME_WEIGHT_KEPT = 10

        if self.data['value'] is None:
            if time.time() - self._last_weight_time > TIME_WEIGHT_KEPT:
                self.data['value'] = 0
        else:
            self._last_weight_time = time.time()

    def _take_measure(self):
        """Reads the device's weight value, and pushes that value to the frontend."""

        if self._is_reading:
            with self._device_lock:
                self._read_weight()
                self._check_last_weight_time()
                if self.data['value'] != self.last_sent_value or self._status['status'] == self.STATUS_ERROR:
                    self.last_sent_value = self.data['value']
                    event_manager.device_changed(self)
        else:
            time.sleep(0.5)

    # Ensures compatibility with Community edition
    def _scale_read_hw_proxy(self):
        """Used when the iot app is not installed"""

        time.sleep(3)
        with self._device_lock:
            self._read_weight()
            self._check_last_weight_time()
        return self.data['value']

    @classmethod
    def supported(cls, device):
        """Checks whether the device at `device` is supported by the driver.

        :param device: path to the device
        :type device: str
        :return: whether the device is supported by the driver
        :rtype: bool
        """

        protocol = cls._protocol

        try:
            with serial_connection(device['identifier'], protocol, is_probing=True) as connection:
                connection.write(protocol.measureCommand + protocol.commandTerminator)
                # Checking whether writing to the serial port using the Adam protocol raises a timeout exception is about the only thing we can do.
                return True
        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s' % (device, protocol.name))
        return False

    def _read_status(self, answer):
        pass
