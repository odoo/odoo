# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from traceback import format_exc
import json
import platform
import logging
from threading import Thread
import time
import urllib3

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

    def __init__(self):
        super().__init__()
        self.hostname = helpers.get_hostname()
        self.mac_address = helpers.get_mac_address()
        self.domain = self._get_domain()
        self.version = helpers.get_version(detailed_version=True)
        self.previous_iot_devices = {}
        self.serial_number = helpers.get_serial_number()

    def _get_domain(self):
        """
        Get the iot box domain based on the IP address and subject.
        """
        subject = helpers.get_conf('subject')
        ip_addr = helpers.get_ip()
        if subject and ip_addr:
            return ip_addr.replace('.', '-') + subject.strip('*')
        return ip_addr or '127.0.0.1'

    def _get_changes_to_send(self):
        """
        Check if the IoT Box information has changed since the last time it was sent.
        Returns True if any tracked property has changed.
        """
        changed = False

        if iot_devices != self.previous_iot_devices:
            self.previous_iot_devices = iot_devices.copy()
            changed = True

        # Mac address can change if the user has multiple network interfaces
        new_mac_address = helpers.get_mac_address()
        if self.mac_address != new_mac_address:
            self.mac_address = new_mac_address
            changed = True
        # IP address change
        new_domain = self._get_domain()
        if self.domain != new_domain:
            self.domain = new_domain
            changed = True
        # Version change
        new_version = helpers.get_version(detailed_version=True)
        if self.version != new_version:
            self.version = new_version
            changed = True

        return changed

    def send_alldevices(self, iot_client=None):
        """
        This method send IoT Box and devices information to Odoo database
        """
        if self.server_url:
            iot_box = {
                'name': self.hostname,
                'identifier': self.mac_address,
                'ip': self.domain,
                'token': helpers.get_token(),
                'serial_number': self.serial_number,
                'version': self.version,
            }
            devices_list = {}
            for device in self.previous_iot_devices.values():
                identifier = device.device_identifier
                devices_list[identifier] = {
                    'name': device.device_name,
                    'type': device.device_type,
                    'manufacturer': device.device_manufacturer,
                    'connection': device.device_connection,
                    'subtype': device.device_subtype if device.device_type == 'printer' else '',
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
            # disable certifiacte verification
            urllib3.disable_warnings()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            try:
                resp = http.request(
                    'POST',
                    self.server_url + "/iot/setup",
                    body=json.dumps(data).encode('utf8'),
                    headers={
                        'Content-type': 'application/json',
                        'Accept': 'text/plain',
                    },
                )
                if iot_client:
                    iot_client.iot_channel = json.loads(resp.data).get('result', '')
            except json.decoder.JSONDecodeError:
                _logger.exception('Could not load JSON data: Received data is not in valid JSON format\ncontent:\n%s', resp.data)
            except Exception:
                _logger.exception('Could not reach configured server to send all IoT devices')
        else:
            _logger.info('Ignoring sending the devices to the database: no associated database')

    def run(self):
        """Thread that will load interfaces and drivers and contact the odoo server with the updates"""
        self.server_url = helpers.get_odoo_server_url()
        helpers.start_nginx_server()

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
            except Exception:
                _logger.exception("Interface %s could not be started", str(interface))

        # Set scheduled actions
        if schedule:
            schedule.every().day.at("00:00").do(helpers.get_certificate_status)
            schedule.every().day.at("00:00").do(helpers.reset_log_level)
            schedule.every().day.at("00:00").do(helpers.check_git_branch)

        # Set up the websocket connection
        if self.server_url and iot_client.iot_channel:
            iot_client.start()
        # Check every 3 seconds if the list of connected devices has changed and send the updated
        # list to the connected DB.
        self.previous_iot_devices = []
        while 1:
            try:
                if self._get_changes_to_send():
                    self.send_alldevices(iot_client)
                time.sleep(3)
                schedule and schedule.run_pending()
            except Exception:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.exception("Manager loop unexpected error")

# Must be started from main thread
if DBusGMainLoop:
    DBusGMainLoop(set_as_default=True)

manager = Manager()
manager.daemon = True
manager.start()
