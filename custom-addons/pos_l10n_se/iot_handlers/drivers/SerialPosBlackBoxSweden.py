# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import serial

from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.iot_handlers.drivers.SerialBaseDriver import SerialDriver, SerialProtocol, serial_connection

_logger = logging.getLogger(__name__)

""" Protocol used for Swedish blackbox to communicate with RS232"""
SwedishBlackboxProtocol = SerialProtocol(
    name="SWEDISH Retail Innovation Cleancash",
    baudrate=9600,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=1,
    writeTimeout=0.3,
    measureRegexp=None,
    statusRegexp=None,
    commandTerminator=b"",
    commandDelay=0.2,
    measureDelay=0.2,
    newMeasureDelay=0.2,
    measureCommand=b"",
    emptyAnswerValid=False,
)

"""Base Json for Swedish black box Messages.
Most of these constants are provided by Retail Innovation Cleancash and should not be changed.
"""
MainStatus = {
    "0": "OK",
    "1": "Warning condition(s) exists",
    "2": "Protocol error condition(s) exists",
    "3": "Non fatal error condition(s) exists",
    "4": "Fatal Error condition(s) exists",
    "5": "Busy (Not used in CCSP v2 currently).",
}

ErrorCode = {
    "001": "Invalid LRC",
    "002": "Unknown message type",
    "003": "Invalid data/parameter",
    "004": "Invalid sequence",
    "005": "Deprecated (Not used)",
    "006": "CleanCash® Not operational",
    "007": "Invalid POS ID",
    "008": "Internal error",
    "009": "License exceeded (CCSP v2)",
    "010": "Internal storage full (CCSP v2)",
    "011": "Invalid sequence number",
}

SeverityError = {
    "0": "Informational",
    "1": "Warning",
    "2": "Protocol error",
    "3": "Non fatal error",
    "4": "Fatal error",
}

StorageStatus = {
    "0": "OK",
    "1": "High level warning",
    "2": "Transaction memory full",
}


class SwedishBlackBoxDriver(SerialDriver):
    """Driver for the Swedish blackbox fiscal data module."""

    _protocol = SwedishBlackboxProtocol

    def __init__(self, identifier, device):
        super().__init__(identifier, device)

        self.device_type = "fiscal_data_module"
        self.data["value"] = device["UnitId"]
        self.serial_number = 0
        self._set_actions()

    @classmethod
    def supported(cls, device):
        """Checks whether the device at path `device` is supported by the driver.
        :param device: path to the device
        :type device: str
        :return: whether the device is supported by the driver
        :rtype: bool
        """

        try:
            protocol = cls._protocol
            packet = cls._wrap_message("SQX")
            with serial_connection(device["identifier"], protocol) as connection:
                response = cls._send_to_blackbox(packet, connection, 2)
                if len(response) > 1 and response[3] == "SRX":
                    device["UnitId"] = cls._get_unit_id(connection)
                    if response[4] != "0":
                        _logger.warning(
                            ("Received error: %s - Severity: %s"),
                            MainStatus.get(response[4]),
                            SeverityError.get(response[5][:2])
                        )
                        _logger.warning("Sent request: %s", packet)
                    return True
        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception(
                "Error while probing %s with protocol %s", device, protocol.name
            )

    @classmethod
    def _get_unit_id(cls, connection):
        """ "Get UnitId of Swedish Black box
        :return: UnitId
        :rtype: string
        """
        try:
            response = cls._request_action("IQ", connection)
            if response[3] == "IR":
                return response[4]
            else:
                _logger.error("Sent IQ request error")
                return False
        except Exception:
            _logger.error("Did not receive a response")

    @staticmethod
    def _lrc(msg):
        """ "Compute a message's longitudinal redundancy check value.
        :param msg: the message the LRC is computed for
        :type msg: byte
        :return: the message LRC
        :rtype: int
        """

        lrc = ord(msg[0])

        for i in range(1, len(msg)):
            lrc ^= ord(msg[i])

        return "{:02x}".format(int(lrc)).upper()

    def _register_receipt(self, data):
        """The register receipt message registers a receipt. CleanCash® responds with Register
        Receipt Response if OK or Negative Acknowledge if error"""

        self.serial_number += 1
        message = {"message_type": "RR", "serial_number": str(self.serial_number)}
        message.update(data.get("high_level_message"))
        request = "#".join(list(message.values()))
        _logger.error(request)
        response = self._request_action(request, self._connection)
        _logger.error(response)
        if len(response) > 1:
            if response[3] == "RRR":
                self.data["signature_control"] = response[4]
                self.data["unit_id"] = response[5]
                self.data["storage_status"] = StorageStatus.get(response[7])
                self.data["status"] = "ok"
            elif response[3] == "NAK":
                _logger.error("Received error: %s", ErrorCode.get(response[4]))
                _logger.error("Sent request: %s received NACK.", request)
                self.data["status"] = ErrorCode.get(response[4])
        else:
            _logger.error("Error request: %s", data)
            _logger.error("Response received: %s", response)
            self.data["status"] = ("Sent request: %s without receiving response.", data)
        event_manager.device_changed(self)

    @classmethod
    def _request_action(cls, data, connection):

        packet = cls._wrap_message(data)
        return cls._send_to_blackbox(packet, connection)

    @classmethod
    def _send_to_blackbox(cls, packet, connection, retry=1):
        """Sends a message to and wait for a response from the blackbox.
        :param packet: the message to be sent to the blackbox
        :type packet: bytearray
        :param response_size: number of bytes of the expected response
        :type response_size: int
        :param connection: serial connection to the blackbox
        :type connection: serial.Serial
        :return: the response to the sent message
        :rtype: bytearray
        """

        ACK = ""
        retries = 0
        while ACK != "ACK" and retries < retry:
            connection.write(packet)
            response = connection.readline().decode().split("#")

            try:
                if response[3] != "NAK":
                    ACK = "ACK"
                else:
                    _logger.error("Received error: %s", ErrorCode.get(response[4]))
                    _logger.error("Sent request: %s received NACK.", packet)
            except Exception:
                _logger.error("sent request: %s without receiving response.", packet)

            retries += 1

        return response

    def _set_actions(self):
        """Initializes `self._actions`, a map of action keys sent by the frontend to backend action methods."""

        self._actions.update(
            {
                "registerReceipt": self._register_receipt,
            }
        )

    @classmethod
    def _wrap_message(cls, high_level_message):
        """Builds a low level message to be sent the blackbox.
        :param high_level_message: The message to be transmitted to the blackbox
        :type high_level_message: str
        :return: The modified message as it is transmitted to the blackbox
        :rtype: bytearray
        """

        length = 11 + len(high_level_message)
        length = "{:03x}".format(int(length)).upper()
        message = "#!#" + length + "#" + high_level_message + "#"
        lrc = cls._lrc(message)
        message += lrc + "\r"

        return message.encode("utf-8")
