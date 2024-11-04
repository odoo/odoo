# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import logging
import subprocess
import requests
from threading import Thread
import time
import urllib3

from odoo.modules.module import get_resource_path
from odoo.addons.hw_drivers.main import iot_devices, manager
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)

class ConnectionManager(Thread):
    def __init__(self):
        super(ConnectionManager, self).__init__()
        self.pairing_code = False
        self.pairing_uuid = False

    def run(self):
        if not helpers.get_odoo_server_url() and not helpers.access_point():
            end_time = datetime.now() + timedelta(minutes=5)
            while (datetime.now() < end_time):
                self._connect_box()
                time.sleep(10)
            self.pairing_code = False
            self.pairing_uuid = False
            self._refresh_displays()

    def _connect_box(self):
        data = {
            'jsonrpc': 2.0,
            'params': {
                'pairing_code': self.pairing_code,
                'pairing_uuid': self.pairing_uuid,
            }
        }

        try:
            urllib3.disable_warnings()
            req = requests.post('https://iot-proxy.odoo.com/odoo-enterprise/iot/connect-box', json=data, verify=False)
            result = req.json().get('result', {})
            if all(key in result for key in ['pairing_code', 'pairing_uuid']):
                self.pairing_code = result['pairing_code']
                self.pairing_uuid = result['pairing_uuid']
            elif all(key in result for key in ['url', 'token', 'db_uuid', 'enterprise_code']):
                self._connect_to_server(result['url'], result['token'], result['db_uuid'], result['enterprise_code'])
        except Exception:
            _logger.exception('Could not reach iot-proxy.odoo.com')

    def _connect_to_server(self, url, token, db_uuid, enterprise_code):
        # Save DB URL and token
        helpers.save_conf_server(url, token, db_uuid, enterprise_code)
        # Notify the DB, so that the kanban view already shows the IoT Box
        manager.send_alldevices()
        # Restart to checkout the git branch, get a certificate, load the IoT handlers...
        helpers.odoo_restart(2)

    def _refresh_displays(self):
        """Refresh all displays to hide the pairing code"""
        for d in iot_devices:
            if iot_devices[d].device_type == 'display':
                iot_devices[d].action({
                    'action': 'display_refresh'
                })

connection_manager = ConnectionManager()
connection_manager.daemon = True
connection_manager.start()
