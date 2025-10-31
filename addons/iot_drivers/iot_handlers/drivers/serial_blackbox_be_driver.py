# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import serial
import time

from odoo.addons.iot_drivers.tools import helpers, system
from odoo.addons.iot_drivers.iot_handlers.drivers.serial_driver_base import SerialDriver, SerialProtocol, serial_connection

_logger = logging.getLogger(__name__)

BlackboxProtocol = SerialProtocol(
    name='Blackbox',
    baudrate=19200,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=3,
    writeTimeout=0.2,
    measureRegexp=None,
    statusRegexp=None,
    commandTerminator=b'',
    commandDelay=0.2,
    measureDelay=0.2,
    newMeasureDelay=0.2,
    measureCommand=b'',
    emptyAnswerValid=False,
)

STX = b'\x02'
ETX = b'\x03'
ACK = b'\x06'
NACK = b'\x15'

errors = {
    '000': "No error",
    '001': "PIN accepted.",
    '101': "Fiscal Data Module memory 90% full.",
    '102': "Already handled request.",
    '103': "No record.",
    '199': "Unspecified warning.",
    '201': "No Vat Signing Card or Vat Signing Card broken.",
    '202': "Please initialize the Vat Signing Card with PIN.",
    '203': "Vat Signing Card blocked.",
    '204': "Invalid PIN.",
    '205': "Fiscal Data Module memory full.",
    '206': "Unknown identifier.",
    '207': "Invalid data in message.",
    '208': "Fiscal Data Module not operational.",
    '209': "Fiscal Data Module real time clock corrupt.",
    '210': "Vat Signing Card not compatible with Fiscal Data Module.",
    '299': "Unspecified error.",
    '300': "Fiscal Data Module responded with invalid response. Check cable and power supply. Restart if necessary.",
    '301': "Fiscal Data Module did not respond. Check cable and power supply. Restart if necessary.",
}


class BlackBoxDriver(SerialDriver):
    """Driver for the blackbox fiscal data module."""

    _protocol = BlackboxProtocol
    priority = 1

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'fiscal_data_module'
        self.sequence_number = 0
        self._set_actions()
        self._certified_ref()

    def _set_actions(self):
        """Initializes `self._actions`, a map of action keys sent by the frontend to backend action methods."""

        self._actions.update({
            'registerReceiptWeb': self._request_registerReceiptWeb,  # 'H' from server (websocket) so requires an answer
            'registerReceipt': self._request_registerReceipt,  # 'H'
            'registerPIN': self._request_registerPIN,  # 'P'
            'status': self._request_status,  # 'S'
        })

    @classmethod
    def supported(cls, device):
        """Checks whether the device at path `device` is supported by the driver.

        :param dict device: path to the device
        :return: whether the device is supported by the driver
        :rtype: bool
        """
        for _ in range(3):
            try:
                protocol = cls._protocol
                probe_message = cls._wrap_low_level_message_around("S000")
                with serial_connection(device['identifier'], protocol) as connection:
                    connection.reset_output_buffer()
                    connection.reset_input_buffer()
                    # ask for status then acknowledge the response
                    connection.write(probe_message)
                    buffer = connection.read_until(ETX)
                    _logger.info('Probing %s as a blackbox. Expecting "%s" in response. Device response: "%s"', device, ACK, buffer)
                    connection.write(ACK)
                    connection.reset_input_buffer()  # flush in case bb sends status again (ACK too late)
                    if len(buffer) > 0 and buffer[0:1] == ACK:
                        return True
            except serial.SerialException:
                _logger.exception('Error while probing %s with protocol %s', device, protocol.name)
            time.sleep(3)
        return False

    def _request_status(self, data):
        """
        Sends a status request to the blackbox and stores the result status in self.data['message']
        """
        packet = self._wrap_low_level_message_around(f'S{str(self.sequence_number % 100).zfill(2)}0')
        self.sequence_number += 1
        blackbox_response = self._send_to_blackbox(packet, self._connection)
        parsed_response = self._parse_blackbox_response(blackbox_response) if blackbox_response else {}
        if not parsed_response:
            self.data['message'] = self.data['result']['error']['errorCode']
        else:
            self.data['message'] = parsed_response.get('error', {}).get('errorCode', '301')

    @classmethod
    def _wrap_low_level_message_around(cls, high_level_message):
        """Builds a low level message to be sent the blackbox.
        :param high_level_message: The message to be transmitted to the blackbox
        :type high_level_message: str
        :return: The modified message as it is transmitted to the blackbox
        :rtype: bytearray
        :return: the response to the sent message, or None if no valid response was received
        """

        bcc = cls._lrc(high_level_message)
        high_level_message_bytes = (ord(b) for b in high_level_message)

        low_level_message = bytearray()
        low_level_message.append(0x02)
        low_level_message.extend(high_level_message_bytes)
        low_level_message.append(0x03)
        low_level_message.append(bcc)

        return low_level_message

    @staticmethod
    def _lrc(msg):
        """Compute a message's longitudinal redundancy check value.

        :param byte msg: the message the LRC is computed for
        :return: the message LRC
        :rtype: int
        """
        lrc = 0
        for character in msg:
            byte = ord(character)
            lrc = (lrc + byte) & 0xFF

        lrc = ((lrc ^ 0xFF) + 1) & 0xFF
        return lrc

    def _box_id(self):
        return 'BODO001' + system.IOT_IDENTIFIER.upper()[-7:]

    def _certified_ref(self):
        self.data['value'] = self._box_id()

    def _parse_blackbox_response(self, response):
        error_code = response[4:10]
        error_message = errors.get(error_code[:3])

        return {
            'identifier': response[0:1],
            'sequence_number': response[1:3],
            'retry_counter': response[3:4],
            'error': {'errorCode': error_code, 'errorMessage': error_message},
            'fdm_number': response[10:21],
            'vsc': response[21:35],
            'date': response[35:43],
            'time': response[43:49],
            'type': response[49:51],
            'ticket_counter': response[51:60],
            'total_ticket_counter': response[60:69],
            'signature': response[69:109]
        }

    def send_blackbox_response(self, data, retry_nbr=0):
        server_url = helpers.get_odoo_server_url() + "/pos_self_blackbox/confirmation"
        try:
            response = requests.post(server_url, json=data, timeout=5)
            response.raise_for_status()
        except requests.Timeout:
            if retry_nbr < 3:
                self.send_blackbox_response(data, retry_nbr + 1)
            else:
                _logger.exception('Could not reach confirmation status URL: %s', server_url)
        except requests.exceptions.RequestException:
            _logger.exception('Could not reach confirmation status URL: %s', server_url)

    def _request_registerReceiptWeb(self, data):
        self._request_registerReceipt(data)

        self.send_blackbox_response({
            'order_id': data['id'],
            'device_identifier': self.device_identifier,
            'blackbox_response': self.data['result'],
            'iot_mac': system.IOT_IDENTIFIER
        })

    def _request_registerReceipt(self, data):
        if data['high_level_message'].get('clock'):
            packet = self._wrap_low_level_message_around(self._wrap_high_level_message_around('I', data['high_level_message']))
            blackbox_response = self._send_to_blackbox(packet, self._connection)

        packet = self._wrap_low_level_message_around(self._wrap_high_level_message_around('H', data['high_level_message']))
        blackbox_response = self._send_to_blackbox(packet, self._connection)
        if blackbox_response:
            self.data['result'] = self._parse_blackbox_response(blackbox_response)

    def _request_registerPIN(self, data):
        packet = self._wrap_low_level_message_around("P040%s" % data['high_level_message'])
        blackbox_response = self._send_to_blackbox(packet, self._connection)
        if blackbox_response:
            self.data['result'] = self._parse_blackbox_response(blackbox_response)

    def _send_to_blackbox(self, packet, connection):
        """Sends a message to and wait for a response from the blackbox.

        :param bytearray packet: the message to be sent to the blackbox
        :param int response_size: number of bytes of the expected response
        :param serial.Serial connection: serial connection to the blackbox
        :return: the response to the message, or None if no valid response was received
        :rtype: bytearray
        """
        connection.reset_output_buffer()
        connection.reset_input_buffer()
        error_code = '301'
        try:
            connection.write(packet)
            buffer = connection.read_until(ETX)
            if len(buffer) and buffer[0:1] == ACK:
                response = buffer[2:-1].decode()  # remove ACK, STX and ETX
                if buffer[1:2] == STX and buffer[-1:] == ETX and self._lrc(response) == ord(connection.read(1)):
                    connection.write(ACK)
                    return response
                _logger.error("received ACK but not a valid response, sending NACK... (response: %s)", buffer)
                connection.write(NACK)
                # no ACK or not a valid response
                error_code = '300'
            elif not len(buffer):
                # When the blackbox is off or poorly connected its adaptor is still detected but always replies with empty bytestrings b''
                _logger.error("Blackbox did not respond, check the cable connection and the power supply.")
        except serial.SerialException:
            _logger.warning("Error while sending to blackbox with protocol %s", self._protocol.name)
        self.data['result'] = {
            'error': {
                'errorCode': error_code,
                'errorMessage': errors[error_code],
            }
        }
        return None

    def _wrap_high_level_message_around(self, request_type, data):
        self.sequence_number += 1
        wrap = request_type + str(self.sequence_number % 100).zfill(2) + '0'

        if request_type == 'I':
            return wrap

        wrap += "{:>8}".format(data['date'])
        wrap += "{:>6}".format(data['ticket_time'])
        wrap += "{:>11}".format(data['insz_or_bis_number'])
        wrap += self._box_id()
        wrap += "{:>6}".format(data['ticket_number'])[-6:]
        wrap += "{:>2}".format(data['type'])
        wrap += "{:>11}".format(data['receipt_total'].zfill(3))[-11:]
        wrap += "2100" + "{:>11}".format(data['vat1'].zfill(3))[-11:]
        wrap += "1200" + "{:>11}".format(data['vat2'].zfill(3))[-11:]
        wrap += " 600" + "{:>11}".format(data['vat3'].zfill(3))[-11:]
        wrap += " 000" + "{:>11}".format(data['vat4'].zfill(3))[-11:]
        wrap += "{:>40}".format(data['plu'])

        return wrap

    def _set_name(self):
        """Tries to build the device's name based on its type and protocol name but falls back on a default name if that doesn't work."""

        try:
            name = '%s serial %s - %s' % (self._protocol.name, self.device_type, self._box_id())
        except Exception:  # noqa: BLE001
            name = 'Unknown Serial Device'
        self.device_name = name

    def run(self):
        with serial_connection(self.device_identifier, self._protocol) as connection:
            self._connection = connection
            self.data['status'] = self.STATUS_CONNECTED
            while not self._stopped.is_set():
                time.sleep(self._protocol.newMeasureDelay)

            self.data['status'] = self.STATUS_DISCONNECTED
