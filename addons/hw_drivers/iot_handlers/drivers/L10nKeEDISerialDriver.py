# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import serial
import time
import struct
import json
from functools import reduce

from odoo import http
from odoo.addons.hw_drivers.iot_handlers.drivers.SerialBaseDriver import SerialDriver, SerialProtocol, serial_connection
from odoo.addons.hw_drivers.main import iot_devices

_logger = logging.getLogger(__name__)

TremolG03Protocol = SerialProtocol(
    name='Tremol G03',
    baudrate=115200,
    bytesize=serial.EIGHTBITS,
    stopbits=serial.STOPBITS_ONE,
    parity=serial.PARITY_NONE,
    timeout=4,
    writeTimeout=0.2,
    measureRegexp=None,
    statusRegexp=None,
    commandTerminator=b'',
    commandDelay=0.2,
    measureDelay=3,
    newMeasureDelay=0.2,
    measureCommand=b'',
    emptyAnswerValid=False,
)

STX = 0x02
ETX = 0x0A
ACK = 0x06
NACK = 0x15

# Dictionary defining the output size of expected from various commands
COMMAND_OUTPUT_SIZE = {
    0x30: 7,
    0x31: 7,
    0x38: 157,
    0x39: 155,
    0x60: 40,
    0x68: 23,
}

FD_ERRORS = {
    0x30: 'OK',
    0x32: 'Registers overflow',
    0x33: 'Clock failure or incorrect date & time',
    0x34: 'Opened fiscal receipt',
    0x39: 'Incorrect password',
    0x3b: '24 hours block - missing Z report',
    0x3d: 'Interrupt power supply in fiscal receipt (one time until status is read)',
    0x3e: 'Overflow EJ',
    0x3f: 'Insufficient conditions',
}

COMMAND_ERRORS = {
    0x30: 'OK',
    0x31: 'Invalid command',
    0x32: 'Illegal command',
    0x33: 'Z daily report is not zero',
    0x34: 'Syntax error',
    0x35: 'Input registers orverflow',
    0x36: 'Zero input registers',
    0x37: 'Unavailable transaction for correction',
    0x38: 'Insufficient amount on hand',
}


class TremolG03Driver(SerialDriver):
    """Driver for the Kenyan Tremol G03 fiscal device."""

    _protocol = TremolG03Protocol

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'fiscal_data_module'
        self.message_number = 0

    @classmethod
    def get_default_device(cls):
        fiscal_devices = list(filter(lambda d: iot_devices[d].device_type == 'fiscal_data_module', iot_devices))
        return len(fiscal_devices) and iot_devices[fiscal_devices[0]]

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
            protocol = cls._protocol
            with serial_connection(device['identifier'], protocol) as connection:
                connection.write(b'\x09')
                time.sleep(protocol.commandDelay)
                response = connection.read(1)
                if response == b'\x40':
                    return True

        except serial.serialutil.SerialTimeoutException:
            pass
        except Exception:
            _logger.exception('Error while probing %s with protocol %s', device, protocol.name)

    # ----------------
    # HELPERS
    # ----------------

    @staticmethod
    def generate_checksum(message):
        """ Generate the checksum bytes for the bytes provided.

        :param message: bytes representing the part of the message from which the checksum is calculated
        :returns:       two checksum bytes calculated from the message

         This checksum is calculated as:
        1) XOR of all bytes of the bytes
        2) Conversion of the one XOR byte into the two bytes of the checksum by
           adding 30h to each half-byte of the XOR

        eg. to_check = \x12\x23\x34\x45\x56
            XOR of all bytes in to_check = \x16
            checksum generated as \x16 -> \x31 \x36
        """
        xor = reduce(lambda a, b: a ^ b, message)
        return bytes([(xor >> 4) + 0x30, (xor & 0xf) + 0x30])

    # ----------------
    # COMMUNICATION
    # ----------------

    def send(self, msgs):
        """ Send and receive messages to/from the fiscal device over serial connection

        Generate the wrapped message from the msgs and send them to the device.
        The wrapping contains the <STX> (starting byte) <LEN> (length byte)
        and <NBL> (message number byte) at the start and two <CS> (checksum
        bytes), and the <ETX> line-feed byte at the end.
        :param msgs: A list of byte strings representing the <CMD> and <DATA>
                     components of the serial message.
        :return:     A list of the responses (if any) from the device. If the
                     response is an ack, it wont be part of this list.
        """

        with self._device_lock:
            replies = []
            for msg in msgs:
                self.message_number += 1
                core_message = struct.pack('BB%ds' % (len(msg)), len(msg) + 34, self.message_number + 32, msg)
                request = struct.pack('B%ds2sB' % (len(core_message)), STX, core_message, self.generate_checksum(core_message), ETX)
                time.sleep(self._protocol.commandDelay)
                self._connection.write(request)
                # If we know the expected output size, we can set the read
                # buffer to match the size of the output.
                output_size = COMMAND_OUTPUT_SIZE.get(msg[0])
                if output_size:
                    try:
                        response = self._connection.read(output_size)
                    except serial.serialutil.SerialTimeoutException:
                        _logger.exception('Timeout error while reading response to command %s', msg)
                        self.data['status'] = "Device timeout error"
                else:
                    time.sleep(self._protocol.measureDelay)
                    response = self._connection.read_all()
                if not response:
                    self.data['status'] = "No response"
                    _logger.error("Sent request: %s,\n Received no response", request)
                    self.abort_post()
                    break
                if response[0] == ACK:
                    # In the case where either byte is not 0x30, there has been an error
                    if response[2] != 0x30 or response[3] != 0x30:
                        self.data['status'] = response[2:4].decode('cp1251')
                        _logger.error(
                            "Sent request: %s,\n Received fiscal device error: %s \n Received command error: %s",
                            request, FD_ERRORS.get(response[2], 'Unknown fiscal device error'),
                            COMMAND_ERRORS.get(response[3], 'Unknown command error'),
                        )
                        self.abort_post()
                        break
                    replies.append('')
                elif response[0] == NACK:
                    self.data['status'] = "Received NACK"
                    _logger.error("Sent request: %s,\n Received NACK \x15", request)
                    self.abort_post()
                    break
                elif response[0] == 0x02:
                    self.data['status'] = "ok"
                    size = response[1] - 35
                    reply = response[4:4 + size]
                    replies.append(reply.decode('cp1251'))
        return {'replies': replies, 'status': self.data['status']}

    def abort_post(self):
        """ Cancel the posting of the invoice

        In the event of an error, it is better to try to cancel the posting of
        the invoice, since the state of the invoice on the device will remain
        open otherwise, blocking further invoices being sent.
        """
        self.message_number += 1
        abort = struct.pack('BBB', 35, self.message_number + 32, 0x39)
        request = struct.pack('B3s2sB', STX, abort, self.generate_checksum(abort), ETX)
        self._connection.write(request)
        response = self._connection.read(COMMAND_OUTPUT_SIZE[0x39])
        if response and response[0] == 0x02:
            self.data['status'] += "\n The invoice was successfully cancelled"
            _logger.info("Invoice successfully cancelled")
        else:
            self.data['status'] += "\n The invoice could not be cancelled."
            _logger.error("Failed to cancel invoice, received response: %s", response)


class TremolG03Controller(http.Controller):

    @http.route('/hw_proxy/l10n_ke_cu_send', type='http', auth='none', cors='*', csrf=False, save_session=False, methods=['POST'])
    def l10n_ke_cu_send(self, messages, company_vat):
        """ Posts the messages sent to this endpoint to the fiscal device connected to the server

        :param messages:     The messages (consisting of <CMD> and <DATA>) to
                             send to the fiscal device.
        :returns:            Dictionary containing a list of the responses from
                             fiscal device and status of the fiscal device.
        """
        device = TremolG03Driver.get_default_device()
        if device:
            # First run the command to get the fiscal device numbers
            device_numbers = device.send([b'\x60'])
            # If the vat doesn't match, abort
            if device_numbers['status'] != 'ok':
                return device_numbers
            serial_number, device_vat, _dummy = device_numbers['replies'][0].split(';')
            if device_vat != company_vat:
                return json.dumps({'status': 'The company vat number does not match that of the device'})
            messages = json.loads(messages)
            resp = json.dumps({**device.send([msg.encode('cp1251') for msg in messages]), 'serial_number': serial_number})
            return resp
        else:
            return json.dumps({'status': 'The fiscal device is not connected to the proxy server'})
