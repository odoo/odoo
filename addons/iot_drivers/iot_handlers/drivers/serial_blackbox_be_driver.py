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
    timeout=1.4,
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
            'batchAction': self._batch_action,  # Batch of multiple actions to be done one after another and send all reponse at once
            'registerReceiptWeb': self._register_receipt_web,  # 'H' from server (websocket) so requires an answer
            'registerReceipt': self._register_receipt,  # 'H'
            'registerPIN': self._register_pin,  # 'P'
            'status': self._request_status,  # 'S'
        })

    @classmethod
    def supported(cls, device):
        """Checks whether the device at path `device` is supported by the driver.

        :param dict device: path to the device
        :return: whether the device is supported by the driver
        :rtype: bool
        """
        protocol = cls._protocol
        for i in range(3):
            try:
                probe_message = cls._wrap_low_level_message_around("S00" + str(i))
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
        """Request the status of the blackbox, used when clicking "Test" button in the UI."""
        blackbox_response = self._send_to_blackbox("S", data, self._connection)
        return self._parse_blackbox_response(blackbox_response)

    @classmethod
    def _wrap_low_level_message_around(cls, high_level_message: str) -> bytes:
        """Builds a low level message to be sent the blackbox.

        :param high_level_message: The message to be transmitted to the blackbox
        :return: The low level message ready to be sent to the blackbox
        """
        data = high_level_message.encode('ascii')
        bcc = cls._lrc(data)
        return STX + data + ETX + bytes([bcc])

    @staticmethod
    def _lrc(msg: bytes) -> int:
        """Compute a message's longitudinal redundancy check value.

        :param msg: the message the LRC is computed for
        :return: the message LRC
        """
        lrc = 0
        for b in msg:
            lrc = (lrc + b) & 0xFF

        return ((lrc ^ 0xFF) + 1) & 0xFF

    @classmethod
    def _box_id(cls):
        return 'BODO001' + system.IOT_IDENTIFIER.upper()[-7:]

    def _certified_ref(self):
        self.data['value'] = self._box_id()

    @classmethod
    def _parse_blackbox_response(cls, response):
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

    def _batch_action(self, batch: dict[str, tuple[dict, str]]):
        """Handles a batch of multiple actions to be done one after another
        and send all response at once.

        :param batch: batch of arrays of action and the data to be sent to the blackbox
        """
        responses = []
        for (data, action) in batch['high_level_message']:
            if action in ('registerReceipt', 'registerPIN'):
                res = self._actions[action](data)
            else:
                _logger.error("Unknown action '%s' in batch", action)
                continue
            responses.append(res)
            if 'error' in res and res['error']['errorCode'][:3] != '000':
                # If the last response was an error, we do not send the next messages in the batch. They will be sent later in a new batch.
                break

        return responses

    def _register_receipt_web(self, data):
        self._register_receipt(data['high_level_message'])

        self.send_blackbox_response({
            'order_id': data['id'],
            'device_identifier': self.device_identifier,
            'blackbox_response': self.data['result'],
            'iot_mac': system.IOT_IDENTIFIER
        })

    def _register_receipt(self, data):
        data = data.get('high_level_message', data)

        if data.get('clock'):
            blackbox_response = self._send_to_blackbox('I', data, self._connection)

        blackbox_response = self._send_to_blackbox('H', data, self._connection)
        if blackbox_response:
            return self._parse_blackbox_response(blackbox_response)
        return None

    def _register_pin(self, data):
        data = data.get('high_level_message', data)

        blackbox_response = self._send_to_blackbox("P", data, self._connection)
        if blackbox_response:
            return self._parse_blackbox_response(blackbox_response)
        return None

    def _send_to_blackbox(self, request_type: str, data: dict, connection: serial.Serial) -> str | dict:
        """Sends a message to and wait for a response from the blackbox.

        :param request_type: "I", "H", "P" or "S"
        :param data: data to be sent to the blackbox
        :param connection: serial connection to the blackbox
        :return: the response to the message, or None if no valid response was received
        """
        error_code = '301'
        for retry in range(3):
            if retry > 0:
                _logger.warning("Retrying (count=%s)...", retry)

            packet = self._wrap_low_level_message_around(self._wrap_high_level_message_around(request_type, data, retry))
            connection.reset_output_buffer()
            connection.reset_input_buffer()
            try:
                connection.write(packet)
                buffer = connection.read_until(ETX)

                if not len(buffer) or buffer[0:1] not in (ACK, NACK):
                    # When the blackbox is off or poorly connected its adaptor is still detected but always replies with empty bytestrings b''
                    _logger.error("Blackbox did not respond, check the cable connection and the power supply.")
                    error_code = '301'
                    continue

                error_code = '301'
                if buffer[0:1] == NACK:
                    _logger.error("received NACK from blackbox.")
                    continue
                elif buffer[0:1] == ACK:
                    buffer = buffer[1:]  # remove ACK
                    for _ in range(3):
                        response_data = buffer[1:-1]  # remove STX and ETX
                        if (
                            len(buffer)
                            and buffer[0:1] == STX
                            and buffer[-1:] == ETX
                            and self._lrc(response_data) == ord(connection.read(1))
                        ):
                            connection.write(ACK)
                            return response_data.decode()

                        _logger.error("received ACK but not a valid response, sending NACK... (response: %s)", buffer)
                        connection.reset_input_buffer()
                        connection.write(NACK)
                        buffer = connection.read_until(ETX)
                    break
            except serial.SerialException:
                _logger.warning("Error while sending to blackbox with protocol %s", self._protocol.name)
                error_code = '300'
        return {
            'error': {
                'errorCode': error_code,
                'errorMessage': errors[error_code],
            }
        }

    def _wrap_high_level_message_around(self, request_type, data, retry=0):
        self.sequence_number += 1
        wrap = request_type + str(self.sequence_number % 100).zfill(2) + str(retry)

        if request_type in ("I", "S"):
            return wrap

        if request_type == "P":
            return wrap + data

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
