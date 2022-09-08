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

    @http.route('/hw_drivers/download_logs', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def download_logs(self):
        """
        Downloads the log file
        """
        if tools.config['logfile']:
            return http.Stream.from_path(tools.config['logfile']).get_response(
                mimetype='text/plain', as_attachment=True
            )
