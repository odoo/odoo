# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
import json
import logging
import os
import subprocess
import time

from odoo import http, tools
from odoo.modules.module import get_resource_path

from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices, manager
from odoo.addons.hw_drivers.tools import helpers

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
            iot_device.action(data)
            return True
        return False

    @http.route('/hw_drivers/check_certificate', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in cron.daily
        """
        helpers.check_certificate()

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

    @http.route('/hw_drivers/box/connect', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def connect_box(self, token):
        """
        This route is called when we want that a IoT Box will be connected to a Odoo DB
        token is a base 64 encoded string and have 2 argument separate by |
        1 - url of odoo DB
        2 - token. This token will be compared to the token of Odoo. He have 1 hour lifetime
        """
        server = helpers.get_odoo_server_url()
        image = get_resource_path('hw_drivers', 'static/img', 'False.jpg')
        if not server:
            credential = b64decode(token).decode('utf-8').split('|')
            url = credential[0]
            token = credential[1]
            if len(credential) > 2:
                # IoT Box send token with db_uuid and enterprise_code only since V13
                db_uuid = credential[2]
                enterprise_code = credential[3]
                helpers.add_credential(db_uuid, enterprise_code)
            try:
                subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/connect_to_server.sh'), url, '', token, 'noreboot'])
                manager.send_alldevices()
                image = get_resource_path('hw_drivers', 'static/img', 'True.jpg')
                helpers.odoo_restart(3)
            except subprocess.CalledProcessError as e:
                _logger.error('A error encountered : %s ' % e.output)
        if os.path.isfile(image):
            with open(image, 'rb') as f:
                return f.read()

    @http.route('/hw_drivers/download_logs', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def download_logs(self):
        """
        Downloads the log file
        """
        if tools.config['logfile']:
            res = http.send_file(tools.config['logfile'], mimetype="text/plain", as_attachment=True)
            res.headers['Cache-Control'] = 'no-cache'
            return res
