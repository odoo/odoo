# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import platform
import requests
import subprocess
from threading import Thread
import time

from odoo.addons.hw_drivers.main import manager, iot_devices
from odoo.addons.hw_drivers.tools import helpers, wifi

_logger = logging.getLogger(__name__)


class ConnectionManager(Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.pairing_code = False
        self.pairing_uuid = False
        self.pairing_code_expired = False
        self.new_database_url = False

        self.iot_box_registered = False
        self.n_times_polled = -1

        if platform.system() == 'Linux':
            self.serial_number = helpers.read_file_first_line('/sys/firmware/devicetree/base/serial-number').strip("\x00")
        else:
            self.serial_number = self._get_serial_number_windows()

        requests.packages.urllib3.disable_warnings()

    def _get_serial_number_windows(self):
        # Get motherboard's uuid (serial number isn't reliable as it's not always present)
        command = [
            'powershell',
            '-Command',
            "(Get-CimInstance Win32_ComputerSystemProduct).UUID"
        ]

        p = subprocess.run(command, stdout=subprocess.PIPE, check=False)
        if p.returncode == 0:
            serial = p.stdout.decode().strip()
            if serial:
                return serial
        else:
            _logger.error("Failed to get Windows IoT serial number")

        return False

    def _register_iot_box(self):
        """ This method is called to register the IoT Box on odoo.com and get a pairing code"""
        req = self._call_iot_proxy()
        if all(key in req for key in ['pairing_code', 'pairing_uuid']):
            self.pairing_code = req['pairing_code']
            self.pairing_uuid = req['pairing_uuid']
            if platform.system() == 'Linux':
                self._try_print_pairing_code()
            self.iot_box_registered = True

    def _get_next_polling_interval(self):
        # To avoid spamming odoo.com with requests we gradually space out the requests
        # e.g If the pairing code is valid for 2 hours this would lead to max 329 requests
        # Starting with 15 seconds and ending with 40s interval, staying under 20s for 50 min
        self.n_times_polled += 1
        return 14 + 1.01 ** self.n_times_polled

    def run(self):
        # Double loop is needed in case the IoT Box isn't initially connected to the internet
        while True:
            while self._should_poll_to_connect_database():
                if not self.iot_box_registered:
                    self._register_iot_box()

                self._poll_pairing_result()
                time.sleep(self._get_next_polling_interval())
            time.sleep(5)

    def _should_poll_to_connect_database(self):
        return (
            not helpers.get_odoo_server_url() and
            helpers.get_ip() and
            not (platform.system() == 'Linux' and wifi.is_access_point()) and
            not self.pairing_code_expired
        )

    def _call_iot_proxy(self):
        data = {
            'params': {
                'pairing_code': self.pairing_code,
                'pairing_uuid': self.pairing_uuid,
                'serial_number': self.serial_number,
            }
        }

        try:
            req = requests.post(
                'https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-box',
                json=data,
                timeout=5,
            )
            req.raise_for_status()
            if req.json().get('error') == 'expired':
                self.pairing_code_expired = True
            return req.json().get('result', {})
        except Exception:
            _logger.exception('Could not reach iot-proxy.odoo.com')
            return {}

    def _poll_pairing_result(self):
        result = self._call_iot_proxy()
        if all(key in result for key in ['url', 'token', 'db_uuid', 'enterprise_code']):
            self._connect_to_server(result['url'], result['token'], result['db_uuid'], result['enterprise_code'])

    def _connect_to_server(self, url, token, db_uuid, enterprise_code):
        self.new_database_url = url
        # Save DB URL and token
        helpers.save_conf_server(url, token, db_uuid, enterprise_code)
        # Notify the DB, so that the kanban view already shows the IoT Box
        manager.send_all_devices()
        # Switch git branch before restarting, this avoids restarting twice
        helpers.check_git_branch()
        # Restart to get a certificate, load the IoT handlers...
        helpers.odoo_restart(2)

    def _try_print_pairing_code(self):
        printers = [device for device in iot_devices.values() if device.device_type == 'printer' and device.connected_by_usb and device.device_subtype in ['receipt_printer', 'label_printer']]
        for printer in printers:
            printer.print_status()


connection_manager = ConnectionManager()
connection_manager.start()
