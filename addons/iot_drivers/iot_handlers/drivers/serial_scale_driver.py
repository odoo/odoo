# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import serial
import time

from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.iot_handlers.drivers.serial_driver_base import SerialDriver, SerialProtocol, serial_connection


_logger = logging.getLogger(__name__)

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


class ScaleDriver(SerialDriver):
    """Driver for the Toldedo 8217 serial scale."""
    _protocol = Toledo8217Protocol
    last_sent_value: float = None

    def __init__(self, identifier: str, device: dict):
        super().__init__(identifier, device)
        self.device_type = "scale"
        self.device_manufacturer = "Toledo"
        self._actions["read_once"] = self._read_once

    def _read_once(self, _):
        """Reads the scale current weight value and pushes it to the frontend."""
        self.last_sent_value = self._read_weight()
        return self.last_sent_value

    def _read_weight(self) -> float:
        """Asks for a new weight from the scale, checks if it is valid
        and, if it is, makes it the current value."""
        self._connection.write(self._protocol.measureCommand + self._protocol.commandTerminator)
        answer = self._get_raw_response()
        match = re.search(self._protocol.measureRegexp, answer)
        if match:
            return float(match.group(1))
        return self._read_status(answer)

    def _take_measure(self):
        """Reads the device's weight value, and pushes that value to the frontend."""
        with self._device_lock:
            weight = self._read_weight()
            if weight != self.last_sent_value or self.data["status"] == "error":
                self.last_sent_value = weight
                self.data.update({"status": "success", "result": weight})
                event_manager.device_changed(self)

    @classmethod
    def supported(cls, device: dict) -> bool:
        protocol = cls._protocol

        try:
            with serial_connection(device['identifier'], protocol, is_probing=True) as connection:
                connection.reset_input_buffer()

                connection.write(b'Ehello' + protocol.commandTerminator)
                time.sleep(protocol.commandDelay)
                answer = connection.read(8)
                if answer == b'\x02E\rhello':
                    connection.write(b'F' + protocol.commandTerminator)
                    connection.reset_input_buffer()
                    return True
        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s', device, protocol.name)
        return False

    @staticmethod
    def _get_raw_response(connection):
        return connection.read_until(b"\r")

    def _read_status(self, answer: bytes) -> float:
        """Status byte in form of an ascii character (Ex: 'D') is sent if scale
        is in motion, or is net/gross weight is negative or over capacity.
        Convert the status byte to a binary string, and check its bits to see if
        there is an error.
        LSB is the last char so the binary string is read in reverse and the first
        char is a parity bit, so we ignore it.

        :param answer: scale answer (Example: b"\x02?D\r")
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
                    _logger.debug(
                        "Scale error: %s. Status string: %s. Scale answer: %s.",
                        status_char_error_bits[index], binary_status_char, answer
                    )
                    self.data.update({"status": "error", "result": 0})
                    return 0.0
        return self.data.get("result", 0.0)
