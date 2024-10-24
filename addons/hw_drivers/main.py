# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from traceback import format_exc
import json
import platform
import logging
from threading import Thread
import time
import requests

from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.websocket_client import WebsocketClient

_logger = logging.getLogger(__name__)

try:
    import schedule
except ImportError:
    schedule = None
    _logger.warning('Could not import library schedule')

try:
    from dbus.mainloop.glib import DBusGMainLoop
except ImportError:
    DBusGMainLoop = None
    _logger.error('Could not import library dbus')

drivers = []
interfaces = {}
iot_devices = {}


class Manager(Thread):
    server_url = None

    def send_alldevices(self, iot_client=None):
        """
        This method send IoT Box and devices information to Odoo database
        """
        if self.server_url:
            subject = helpers.get_conf('subject')
            if subject:
                domain = helpers.get_ip().replace('.', '-') + subject.strip('*')
            else:
                domain = helpers.get_ip()
            iot_box = {
                'name': helpers.get_hostname(),
                'identifier': helpers.get_mac_address(),
                'ip': domain,
                'token': helpers.get_token(),
                'version': helpers.get_version(detailed_version=True),
            }
            devices_list = {}
            for device in iot_devices:
                identifier = iot_devices[device].device_identifier
                devices_list[identifier] = {
                    'name': iot_devices[device].device_name,
                    'type': iot_devices[device].device_type,
                    'manufacturer': iot_devices[device].device_manufacturer,
                    'connection': iot_devices[device].device_connection,
                    'subtype': iot_devices[device].device_subtype if iot_devices[device].device_type == 'printer' else '',
                }
            devices_list_to_send = {
                key: value for key, value in devices_list.items() if key != 'distant_display'
            }
            data = {
                'params': {
                    'iot_box': iot_box,
                    'devices': devices_list_to_send,
                }  # Don't send distant_display to the db
            }
            try:
                resp = requests.post(
                    self.server_url + "/iot/setup",
                    data=json.dumps(data),
                    headers={
                        'Content-type': 'application/json',
                        'Accept': 'application/json',
                    },
                )
                if resp.ok and iot_client:
                    data = resp.json().get('result', {})
                    iot_client.iot_channel = data.get('iot_channel', '')
            except json.decoder.JSONDecodeError:
                _logger.exception(
                    'Could not load JSON data: Received data is not in valid JSON format\ncontent:\n%s',
                    data
                )
            except Exception:
                _logger.exception('Could not reach configured server')
        else:
            _logger.info('Ignoring sending the devices to the database: no associated database')

    def _ensure_db_info(self):
        """Fetch the ``db_uuid`` and ``enterprise_code`` from the server
        and update the configuration file.
        It will only fetch the data if the configuration file does not have the required data.
        """
        if not self.server_url:
            return

        db_uuid = helpers.get_conf('db_uuid')
        enterprise_code = helpers.get_conf('enterprise_code')
        # if db_uuid or enterprise_code is empty, fetch the data from the server
        if not db_uuid or not enterprise_code:
            try:
                response = requests.post(
                    self.server_url + "/iot/db_info",
                    data=json.dumps({
                        'params': {
                            'identifier': helpers.get_mac_address(),
                            'db_uuid': not db_uuid,
                            'enterprise_code': not enterprise_code,
                        }
                    }),
                    headers={
                        'Content-type': 'application/json',
                        'Accept': 'application/json',
                    },
                )
                response.raise_for_status()

                data = response.json().get('result', {})
                helpers.update_conf(data)
            except requests.exceptions.HTTPError as e:
                _logger.warning('Failed to fetch db_uuid and enterprise_code from the db: %s', e)

    def run(self):
        """
        Thread that will load interfaces and drivers and contact the odoo server with the updates
        """
        self.server_url = helpers.get_odoo_server_url()
        helpers.start_nginx_server()
        self._ensure_db_info()

        _logger.info("IoT Box Image version: %s", helpers.get_version(detailed_version=True))
        if platform.system() == 'Linux' and self.server_url:
            helpers.check_git_branch()
            helpers.generate_password()
        is_certificate_ok, certificate_details = helpers.get_certificate_status()
        if not is_certificate_ok and certificate_details != 'ERR_IOT_HTTPS_CHECK_NO_SERVER':
            _logger.warning("An error happened when trying to get the HTTPS certificate: %s",
                            certificate_details)

        iot_client = self.server_url and WebsocketClient(self.server_url)
        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self.send_alldevices(iot_client)
        helpers.download_iot_handlers()
        helpers.load_iot_handlers()

        # Start the interfaces
        for interface in interfaces.values():
            try:
                i = interface()
                i.daemon = True
                i.start()
            except Exception as e:
                _logger.error("Error in %s: %s", str(interface), e)

        # Set scheduled actions
        schedule and schedule.every().day.at("00:00").do(helpers.get_certificate_status)

        # Set up the websocket connection
        if self.server_url and iot_client.iot_channel:
            iot_client.start()
        # Check every 3 seconds if the list of connected devices has changed and send the updated
        # list to the connected DB.
        self.previous_iot_devices = []
        while 1:
            try:
                if iot_devices != self.previous_iot_devices:
                    self.previous_iot_devices = iot_devices.copy()
                    self.send_alldevices(iot_client)
                time.sleep(3)
                schedule and schedule.run_pending()
            except Exception:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.error(format_exc())

# Must be started from main thread
if DBusGMainLoop:
    DBusGMainLoop(set_as_default=True)

manager = Manager()
manager.daemon = True
manager.start()
