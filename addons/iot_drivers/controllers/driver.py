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

from odoo.addons.iot_drivers.event_manager import event_manager
from odoo.addons.iot_drivers.tools import communication, helpers, route
from odoo.addons.iot_drivers.tools.system import IOT_IDENTIFIER

_logger = logging.getLogger(__name__)

DEVICE_TYPES = [
    "display", "printer", "scanner", "keyboard", "camera", "device", "payment", "scale", "fiscal_data_module"
]


class DriverController(http.Controller):
    @helpers.toggleable
    @route.iot_route(['/iot_drivers/action', '/hw_drivers/action'], type='jsonrpc', cors='*', csrf=False)
    def action(self, session_id, device_identifier, data):
        """This route is called when we want to make an action with device (take picture, printing,...)
        We specify in data from which session_id that action is called
        And call the action of specific device
        """
        if isinstance(data, str):
            data = json.loads(data)

        message_type = data.get('action', 'test_protocol') if device_identifier == IOT_IDENTIFIER else 'iot_action'

<<<<<<< 3575815c2297510655df21b1b83cff72ff36ddba
        return communication.handle_message(
            message_type, 'lp', session_id=session_id, device_identifier=device_identifier, **data
        )
||||||| dea5a1d28a1935c2b4d87c3c6e8c07cd874c7d6b
        if not iot_device:
            _logger.warning("IoT Device with identifier %s not found", device_identifier)
            return False

        data['session_id'] = session_id  # ensure session_id is in data as for websocket communication
        _logger.debug("Calling action %s for device %s", data.get('action', ''), device_identifier)
        iot_device.action(data)
        return True

    @route.iot_route('/iot_drivers/check_certificate', type='http', cors='*', csrf=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in iot-box cron.daily, deprecated since image 24_10 but needed for compatibility with the image 24_01
        """
        helpers.get_certificate_status()
=======
        if not iot_device:
            _logger.warning("IoT Device with identifier %s not found", device_identifier)
            return False

        data['session_id'] = session_id  # ensure session_id is in data as for websocket communication
        start_operation_time = time.perf_counter()
        _logger.info("Longpolling: calling action %s for device %s", data.get('action', ''), device_identifier)
        iot_device.action(data)
        _logger.info("device '%s' action finished - %.*f", device_identifier, 3, time.perf_counter() - start_operation_time)
        return True

    @route.iot_route('/iot_drivers/check_certificate', type='http', cors='*', csrf=False)
    def check_certificate(self):
        """
        This route is called when we want to check if certificate is up-to-date
        Used in iot-box cron.daily, deprecated since image 24_10 but needed for compatibility with the image 24_01
        """
        helpers.get_certificate_status()
>>>>>>> e2ec846fdb3c4eaddda4858d88ff21348cd216ce

    @helpers.toggleable
    @route.iot_route(['/iot_drivers/event', '/hw_drivers/event'], type='jsonrpc', cors='*', csrf=False)
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
                _logger.debug("Event %s found for device %s ", event, event['device_identifier'])
                return event

        # Wait for new event
        if req['event'].wait(50):
            req['event'].clear()
            req['result']['session_id'] = req['session_id']
            return req['result']

    @route.iot_route(['/iot_drivers/download_logs', '/hw_drivers/download_logs'], type='http', cors='*', csrf=False)
    def download_logs(self):
        """
        Downloads the log file
        """
        log_path = tools.config['logfile'] or "/var/log/odoo/odoo-server.log"
        try:
            stat = os.stat(log_path)
        except FileNotFoundError:
            raise InternalServerError("Log file has not been found. Check your Log file configuration.")
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
