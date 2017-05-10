# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import serial
import subprocess
from os.path import isfile
from os import listdir
from threading import Thread, Lock

from odoo import http

import odoo.addons.hw_proxy.controllers.main as hw_proxy

_logger = logging.getLogger(__name__)

DRIVER_NAME = 'fiscal_data_module'

class Blackbox(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.blackbox_lock = Lock()
        self.set_status('connecting')
        self.device_path = self._find_device_path_by_probing()

    def set_status(self, status, messages=[]):
        self.status = {
            'status': status,
            'messages': messages
        }

    def get_status(self):
        return self.status

    # There is no real way to find a serial device, all you can really
    # find is the name of the serial to usb interface, which in the
    # case of the blackbox is not defined because it doesn't always
    # come with it's own interface (eg. Retail Cleancash SC-B). So, in
    # order to differentiate between other devices like this, what
    # we'll do is probe every serial device with an FDM status
    # request. The first device to give an answer that makes sense
    # wins.
    def _find_device_path_by_probing(self):
        with hw_proxy.rs232_lock:
            path = "/dev/serial/by-path/"
            probe_message = self._wrap_low_level_message_around("S000")

            try:
                devices = listdir(path)
            except OSError:
                _logger.warning(path + " doesn't exist")
                self.set_status("disconnected", ["No RS-232 device (or emulated ones) found"])
            else:
                for device in devices:
                    if device in hw_proxy.rs232_devices:
                        continue
                    path_to_device = path + device
                    _logger.debug("Probing " + device)

                    if self._send_to_blackbox(probe_message, 21, path_to_device, just_wait_for_ack=True):
                        _logger.info(device + " will be used as the blackbox")
                        self.set_status("connected", [device])
                        hw_proxy.rs232_devices[device] = DRIVER_NAME
                        return path_to_device

                _logger.warning("Blackbox could not be found")
                self.set_status("disconnected", ["Couldn't find the Fiscal Data Module"])
                return ""

    def _lrc(self, msg):
        lrc = 0

        for character in msg:
            byte = ord(character)
            lrc = (lrc + byte) & 0xFF

        lrc = ((lrc ^ 0xFF) + 1) & 0xFF

        return lrc

    def _wrap_low_level_message_around(self, high_level_message):
        bcc = self._lrc(high_level_message)
        high_level_message_bytes = (ord(b) for b in high_level_message)

        low_level_message = bytearray()
        low_level_message.append(0x02)
        low_level_message.extend(high_level_message_bytes)
        low_level_message.append(0x03)
        low_level_message.append(bcc)

        return low_level_message

    def _send_and_wait_for_ack(self, packet, serial):
        ack = 0
        MAX_RETRIES = 1

        while ack != 0x06 and int(chr(packet[4])) < MAX_RETRIES:
            serial.write(packet)
            ack = serial.read(1)

            # This violates the principle that we do high level
            # client-side and low level posbox-side but the retry
            # counter is always in a fixed position in the high level
            # message so it's safe to do it. Also it would be a pain
            # to have to throw this all the way back to js just so it
            # can increment the retry counter and then try again.
            packet = packet[:4] + str(int(packet[4]) + 1) + packet[5:]

            if ack:
                ack = ord(ack)
            else:
                _logger.warning("did not get ACK, retrying...")
                ack = 0

        if ack == 0x06:
            return True
        else:
            _logger.error("retried " + str(MAX_RETRIES) + " times without receiving ACK, is blackbox properly connected?")
            return False

    def _send_to_blackbox(self, packet, response_size, device_path, just_wait_for_ack=False):
        if not device_path:
            return ""

        ser = serial.Serial(port=device_path,
                            baudrate=19200,
                            timeout=3)
        MAX_NACKS = 1
        got_response = False
        sent_nacks = 0

        if self._send_and_wait_for_ack(packet, ser):
            if just_wait_for_ack:
                return True

            while not got_response and sent_nacks < MAX_NACKS:
                stx = ser.read(1)
                response = ser.read(response_size)
                etx = ser.read(1)
                bcc = ser.read(1)

                if stx == chr(0x02) and etx == chr(0x03) and bcc and self._lrc(response) == ord(bcc):
                    got_response = True
                    ser.write(chr(0x06))
                else:
                    _logger.warning("received ACK but not a valid response, sending NACK...")
                    sent_nacks += 1
                    ser.write(chr(0x15))

            if not got_response:
                _logger.error("sent " + str(MAX_NACKS) + " NACKS without receiving response, giving up.")
                return ""

            ser.close()
            return response
        else:
            ser.close()
            return ""

if isfile("/home/pi/registered_blackbox_be"):
    blackbox_thread = Blackbox()
    hw_proxy.drivers[DRIVER_NAME] = blackbox_thread

    class BlackboxDriver(hw_proxy.Proxy):
        @http.route('/hw_proxy/request_blackbox/', type='json', auth='none', cors='*')
        def request_blackbox(self, high_level_message, response_size):
            to_send = blackbox_thread._wrap_low_level_message_around(high_level_message)

            with blackbox_thread.blackbox_lock:
                response = blackbox_thread._send_to_blackbox(to_send, response_size, blackbox_thread.device_path)

            return response

        @http.route('/hw_proxy/request_serial/', type='json', auth='none', cors='*')
        def request_serial(self):
            return subprocess.check_output("ifconfig eth0 | grep -o 'HWaddr.*' | sed 's/HWaddr \\(.*\\)/\\1/' | sed 's/://g'", shell=True).rstrip()[-7:]
