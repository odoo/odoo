# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import platform
import requests
from threading import Thread
import time

from odoo.addons.hw_drivers.main import manager
from odoo.addons.hw_drivers.tools import helpers, wifi

_logger = logging.getLogger(__name__)

# We use a timeout slightly less than the IoT proxy so
# that there is a grace period between codes
PAIRING_CODE_TIMEOUT_SECONDS = 580

MAXIMUM_NUMBER_OF_CODES = 3


class ConnectionManager(Thread):
    def __init__(self):
        super(ConnectionManager, self).__init__()
        self.pairing_code = False
        self.pairing_uuid = False
        self.pairing_code_expires = 0
        self.pairing_code_count = 0
        self.running = False
        requests.packages.urllib3.disable_warnings()

    def run(self):
        self.running = True
        while self.running:
            if self._should_fetch_pairing_code():
                if time.monotonic() > self.pairing_code_expires:
                    self._refresh_pairing_code()
                else:
                    self._poll_pairing_result()
            else:
                self.running = False
                self.pairing_code = False
                self.pairing_uuid = False
                self.pairing_code_expires = 0
            time.sleep(10)

    def _should_fetch_pairing_code(self):
        return (
            not helpers.get_odoo_server_url() and
            helpers.get_ip() and
            not (platform.system() == 'Linux' and wifi.is_access_point()) and
            self.pairing_code_count <= MAXIMUM_NUMBER_OF_CODES
        )

    def _call_iot_proxy(self, pairing_code, pairing_uuid):
        data = {
            'jsonrpc': 2.0,
            'params': {
                'pairing_code': pairing_code,
                'pairing_uuid': pairing_uuid,
            }
        }

        try:
            req = requests.post(
                'https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-box', json=data, verify=False, timeout=5
            )
            return req.json().get('result', {})
        except Exception:
            _logger.exception('Could not reach iot-proxy.odoo.com')
            return {}

    def _poll_pairing_result(self):
        result = self._call_iot_proxy(self.pairing_code, self.pairing_uuid)
        
        if all(key in result for key in ['url', 'token', 'db_uuid', 'enterprise_code']):
            self._connect_to_server(result['url'], result['token'], result['db_uuid'], result['enterprise_code'])

    def _refresh_pairing_code(self):
        result = self._call_iot_proxy(pairing_code=None, pairing_uuid=None)

        if all(key in result for key in ['pairing_code', 'pairing_uuid']):
            self.pairing_code = result['pairing_code']
            self.pairing_uuid = result['pairing_uuid']
            self.pairing_code_expires = time.monotonic() + PAIRING_CODE_TIMEOUT_SECONDS
            self.pairing_code_count += 1

    def _connect_to_server(self, url, token, db_uuid, enterprise_code):
        # Save DB URL and token
        helpers.save_conf_server(url, token, db_uuid, enterprise_code)
        # Notify the DB, so that the kanban view already shows the IoT Box
        manager.send_all_devices()
        # Restart to checkout the git branch, get a certificate, load the IoT handlers...
        helpers.odoo_restart(2)


connection_manager = ConnectionManager()
connection_manager.daemon = True
connection_manager.start()
