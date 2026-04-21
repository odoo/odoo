# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import serial

from odoo.addons.iot_drivers.iot_handlers.drivers.serial_driver_base import SerialDriver, SerialProtocol, serial_connection

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
        self.unit_id = device["unit_id"]
        self.protocol_version = device["protocol_version"]
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
            packet = cls._wrap_message("SIQ")
            with serial_connection(device["identifier"], protocol) as connection:
                response = cls._send_to_blackbox(packet, connection, 2)
                if len(response) > 1 and response[3] == "SIR":
                    identity = cls._get_identity(connection)
                    if not identity:
                        return False
                    device["unit_id"] = identity["unit_id"]
                    device["protocol_version"] = identity["protocol_version"]
                    if response[4] != "0":
                        _logger.warning(
                            ("Received error: %s - Severity: %s"),
                            MainStatus.get(response[4]),
                            SeverityError.get(response[5][1:2])
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
    def _get_identity(cls, connection):
        """ "Get Identity of Swedish Black box
        :return: dictionary containing unit_id, protocol_version, firmware_version
        :rtype: dict
        """
        try:
            response = cls._request_action("IQ", connection)
            if response[3] == "IR":
                return {
                    "unit_id": response[4],
                    "protocol_version": int(response[5]),
                    "firmware_version": response[6],
                }
            else:
                _logger.error("Sent IQ request error")
                return False
        except Exception:  # noqa: BLE001
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

        return f"{int(lrc):02X}"

    def _check_error(self, request, response):
        if len(response) <= 1:
            _logger.error("Error request: %s", request)
            _logger.error("Response received: %s", response)
            return {"error": f"Sent request: {request} without receiving response."}

        if len(response) >= 4 and response[3] == "NAK":
            _logger.error("Received error: %s", ErrorCode.get(response[4]))
            _logger.error("Sent request: %s received NACK.", request)
            return {"error": ErrorCode.get(response[4])}

        return None

    def _register_receipt(self, data):
        if self.protocol_version >= 2:
            return self._register_receipt_v2(data)
        else:
            return self._register_receipt_v1(data)

    def _register_receipt_v2(self, data):
        """The register receipt message registers a receipt (CCSP v2 only).
        CleanCash® responds with Register Receipt Response if OK or Negative Acknowledge if error"""

        self.serial_number += 1
        message = {"message_type": "RR", "serial_number": str(self.serial_number)}
        message.update(data.get("high_level_message"))
        request = "#".join(list(message.values()))
        response = self._request_action(request, self._connection)

        return self._check_error(request, response) or {
            "signature_control": response[4],
            "unit_id": response[5],
            "storage_status": StorageStatus.get(response[7]),
        }

    def _register_receipt_v1(self, data):
        """CCSP v1 requires three commands to register a receipt:
           ST (start receipt), RH (receipt header), SQ (signature request)"""

        response = self._request_action("ST", self._connection)
        error = self._check_error("ST", response)
        if error:
            return error

        message_fields = list(data.get("high_level_message").values())
        request_fields = ["RH", *message_fields[0:3], " ", " ", *message_fields[3:]]
        request = "#".join(request_fields)
        response = self._request_action(request, self._connection)
        error = self._check_error(request, response)
        if error:
            return error

        response = self._request_action("SQ", self._connection)

        return self._check_error("SQ", response) or {
            "signature_control": response[4],
            "unit_id": self.unit_id,
        }

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
        connection.reset_input_buffer()
        connection.reset_output_buffer()

        ACK = ""
        retries = 0
        while ACK != "ACK" and retries < retry:
            connection.write(packet)
            response = connection.readline().decode(errors="ignore").split("#")

            try:
                if response[3] != "NAK":
                    ACK = "ACK"
                else:
                    _logger.error("Received error: %s", ErrorCode.get(response[4]))
                    _logger.error("Sent request: %s received NACK.", packet)
            except Exception:  # noqa: BLE001
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
        length = f"{int(length):03X}"
        message = "#!#" + length + "#" + high_level_message + "#"
        lrc = cls._lrc(message)
        message += lrc + "\r"

        return message.encode("utf-8")


SkattedosanBlackboxProtocol = SerialProtocol(
    name="Swedish Skattedosan",
    baudrate=57600,
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


SkattedosanReturnCodes = {
    "24": "Internal log is full",
    "23": "Error in an internal counter",
    "22": "Field is present after field CRC",
    "21": "Relationship between sales amount and return amount is wrong",
    "20": "Power fail abort",
    "19": "Internal error in the control unit",
    "18": "Internal error in the control unit",
    "17": "Internal error in the control unit",
    "16": "Internal error in the control unit",
    "15": "Internal error in the control unit",
    "13": "Wrong format of VAT D",
    "12": "Wrong format of VAT C",
    "11": "Wrong format of VAT B",
    "10": "Wrong format of VAT A",
    "9": "Wrong format of sales amount",
    "8": "Wrong format of return amount",
    "7": "Type of receipt not defined",
    "6": "Type of receipt not defined",
    "5": "Wrong format of serial number",
    "4": "Wrong format of cash register ID",
    "3": "Wrong format of organisation number",
    "2": "Wrong date/time range",
    "1": "Wrong number of arguments",
    "0": "OK",
    "-1": "Wrong length",
    "-2": "CRC error",
    "-3": "Unknown command",
}


class SkattedosanBlackBoxDriver(SerialDriver):
    _protocol = SkattedosanBlackboxProtocol

    def __init__(self, identifier: str, device: dict[str, str]):
        super().__init__(identifier, device)

        self.device_type = "fiscal_data_module"
        self.unit_id = device["unit_id"]
        self.serial_number = 0
        self._actions.update({
            "registerReceipt": self._register_receipt,
        })

    @classmethod
    def supported(cls, device: dict[str, str]):
        try:
            with serial_connection(device["identifier"], cls._protocol) as connection:
                response = cls._send_to_blackbox(connection, "ver")
                if response:
                    device["unit_id"] = response[4]
                    return True
        except serial.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception(
                "Error while probing %s with protocol %s", device, cls._protocol.name
            )

    @staticmethod
    def _crc16(message: str):
        crc = 0
        for byte in message.encode():
            crc = crc ^ (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        crc &= 0xffff

        return f"0x{crc:04X}"

    def _register_receipt(self, data: dict[str, dict[str, str]]):
        self.serial_number += 1
        args = data["high_level_message"]
        message = [
            "kd",
            args["date"],
            args["organisation_number"],
            args["pos_id"],
            str(self.serial_number),
            args["receipt_type"],
            args["negative_total"],
            args["receipt_total"],
            args["vat1"].strip() or "25,00;0,00",
            args["vat2"].strip() or "12,00;0,00",
            args["vat3"].strip() or "6,00;0,00",
            args["vat4"].strip() or "0,00;0,00",
        ]
        response = self._send_to_blackbox(self._connection, *message)

        if response is None:
            return None

        return {
            "signature_control": response[0] if response else "",
            "unit_id": self.unit_id,
        }

    @classmethod
    def _send_to_blackbox(cls, connection: serial.Serial, *args: str):
        connection.reset_input_buffer()
        connection.reset_output_buffer()

        packet = cls._wrap_message(*args)
        max_retries = 3
        for attempt in range(1, max_retries):
            _logger.info("Sending command (attempt %d): %s", attempt, packet)

            try:
                connection.write(packet)
                response = connection.read_until(b"\r").decode().split()
            except serial.SerialException:
                _logger.exception("Failed to send command")
                continue

            _logger.info("Response received: %s", response)

            return_code = response[0]
            crc = response[-1]
            data = response[1:-1]
            expected_crc = cls._crc16(" ".join(response[:-1]) + " ")

            if crc != expected_crc:
                _logger.warning("Bad checksum: expected %s, received %s", expected_crc, crc)
                continue

            if return_code != "0":
                _logger.error("Received error: %s", SkattedosanReturnCodes.get(return_code))
                continue

            return data

        return None

    @classmethod
    def _wrap_message(cls, *args: str):
        message_without_crc = " ".join(args) + " "

        return f"{message_without_crc}{cls._crc16(message_without_crc)}\r\n".encode()
