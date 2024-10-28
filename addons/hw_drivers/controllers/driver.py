# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import json
import logging
import os
from socket import gethostname
import time
from werkzeug.exceptions import InternalServerError
from zlib import adler32

from odoo import http, tools

from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)


class DriverController(http.Controller):
    @http.route('/hw_drivers/action', type='jsonrpc', auth='none', cors='*', csrf=False, save_session=False)
    def action(self, session_id, device_identifier, action='', **kwargs):
        """This route is called when we want to make an action with device (take picture, printing,...)
        We specify in data from which session_id that action is called
        And call the action of specific device

        :param str session_id: the session id of the request
        :param str device_identifier: the identifier of the device
        :param str action: the action to be executed
        :param dict kwargs: the parameters to be passed to the action method
        """
        iot_device = iot_devices.get(device_identifier)
        # Skip the request if it was already executed (duplicated action calls)
        if not iot_device or not iot_device.is_idempotent(session_id, **kwargs):
            return False

        iot_device.data['owner'] = session_id
        iot_device.action(action=action, **kwargs)  # Call action method on device
        return True

    @http.route('/hw_drivers/check_certificate', type='http', auth='none', cors='*', csrf=False, save_session=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in iot-box cron.daily, deprecated since image 24_10 but needed for compatibility with the image 24_01
        """
        helpers.get_certificate_status()

    @http.route('/hw_drivers/event', type='jsonrpc', auth='none', cors='*', csrf=False, save_session=False)
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
        log_path = tools.config['logfile']
        if not log_path:
            raise InternalServerError("Log file configuration is not set")
        try:
            stat = os.stat(log_path)
        except FileNotFoundError:
            raise InternalServerError("Log file has not been found")
        check = adler32(log_path.encode())
        log_file_name = f"iot-odoo-{gethostname()}-{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        # intentionally don't use Stream.from_path as the path used is not in the addons path
        # for instance, for the iot-box it will be in /var/log/odoo
        return http.Stream(
                type='path',
                path=log_path,
                download_name=log_file_name,
                etag=f'{int(stat.st_mtime)}-{stat.st_size}-{check}',
                last_modified=stat.st_mtime,
                size=stat.st_size,
                mimetype='text/plain',
            ).get_response(
            mimetype='text/plain', as_attachment=True
        )
