# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from datetime import datetime
import json
import logging
import os
from socket import gethostname
import subprocess
import time
from werkzeug.exceptions import Forbidden

from odoo import http, tools
from odoo.modules.module import get_resource_path
from odoo.tools import date_utils
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices, manager
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.tools.iot_object_info_controller import IoTObjectInfoController

_logger = logging.getLogger(__name__)


class DriverController(http.Controller):
    @http.route('/hw_drivers/action', type='json', auth='none', cors='*', csrf=False, save_session=False)
    def action(self, session_id, device_identifier, data):
        """
        This route is called when we want to make a action with device (take picture, printing,...)
        We specify in data from which session_id that action is called
        And call the action of specific device
        """
        iot_device = iot_devices.get(device_identifier)
        if iot_device:
            iot_device.data['owner'] = session_id
            data = json.loads(data)

            # Skip the request if it was already executed (duplicated action calls)
            iot_idempotent_id = data.get("iot_idempotent_id")
            if iot_idempotent_id:
                idempotent_session = iot_device._check_idempotency(iot_idempotent_id, session_id)
                if idempotent_session:
                    _logger.info("Ignored request from %s as iot_idempotent_id %s already received from session %s",
                                 session_id, iot_idempotent_id, idempotent_session)
                    return False
            iot_device.action(data)
            return True
        return False

    @http.route('/hw_drivers/check_certificate', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in cron.daily
        """
        helpers.get_certificate_status()

    @http.route('/hw_drivers/event', type='json', auth='none', cors='*', csrf=False, save_session=False)
    def event(self, listener):
        """
        listener is a dict in witch there are a sessions_id and a dict of device_identifier to listen
        """
        req = event_manager.add_request(listener)

        # Search for previous events and remove events older than 5 seconds
        oldest_time = time.time() - 5
        for event in list(event_manager.events):
            if event['time'] < oldest_time:
                del event_manager.events[0]
                continue
            if event['device_identifier'] in listener['devices'] and event['time'] > listener['last_event']:
                event['session_id'] = req['session_id']
                return event

        # Wait for new event
        if req['event'].wait(50):
            req['event'].clear()
            req['result']['session_id'] = req['session_id']
            return req['result']

    @http.route('/hw_drivers/download_logs', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def download_logs(self):
        """
        Downloads the log file
        """
        if tools.config['logfile']:
            res = http.send_file(tools.config['logfile'], mimetype="text/plain", as_attachment=True)
            res.headers['Cache-Control'] = 'no-cache'
            return res

    @http.route('/hw_drivers/download_iot_info', type='http', auth='none', methods=['POST'], csrf=False, cors='*')
    def download_iot_info(self, iot_security_token):
        if not helpers.check_iot_security_token(iot_security_token):
            raise Forbidden("Invalid IoT security token")

        iot_info_json_b = str.encode(
            json.dumps(
                IoTObjectInfoController.get_all_iot_info(),
                ensure_ascii=False,
                default=date_utils.json_default
            )
        )
        response = http.Stream(
            type='data',
            data=iot_info_json_b,
            download_name=f"iot-odoo-info-{gethostname()}-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
        ).get_response(as_attachment=True)
        # As it's a CORS request, the Content-Disposition header is not exposed by default, see:
        # https://stackoverflow.com/a/5837798
        response.headers.set('Access-Control-Expose-Headers', "Content-Disposition")
        return response
