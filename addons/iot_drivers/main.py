# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import schedule
import subprocess
from threading import Thread
import time

from odoo.addons.iot_drivers.tools import certificate, helpers, upgrade, wifi
from odoo.addons.iot_drivers.tools.system import IS_RPI
from odoo.addons.iot_drivers.websocket_client import WebsocketClient

if IS_RPI:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)  # Must be started from main thread

_logger = logging.getLogger(__name__)

drivers = []
interfaces = {}
iot_devices = {}
unsupported_devices = {}


class Manager(Thread):
    daemon = True
    ws_channel = ""

    def __init__(self):
        super().__init__()
        self.identifier = helpers.get_identifier()
        self.domain = self._get_domain()
        self.version = helpers.get_version(detailed_version=True)
        self.previous_iot_devices = {}
        self.previous_unsupported_devices = {}

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

        current_devices = set(iot_devices.keys()) | set(unsupported_devices.keys())
        previous_devices = set(self.previous_iot_devices.keys()) | set(self.previous_unsupported_devices.keys())
        if current_devices != previous_devices:
            self.previous_iot_devices = iot_devices.copy()
            self.previous_unsupported_devices = unsupported_devices.copy()
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

    @helpers.require_db
    def _send_all_devices(self, server_url=None):
        """This method send IoT Box and devices information to Odoo database

        As the server can be down or not started yet (in case of local testing),
        we retry to send the data several times with a delay between each attempt.

        :param server_url: URL of the Odoo server (provided by decorator).
        """
        iot_box = {
            'identifier': self.identifier,
            'ip': self.domain,
            'token': helpers.get_token(),
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
        devices_list.update(self.previous_unsupported_devices)
        devices_list_to_send = {
            key: value for key, value in devices_list.items() if key != 'distant_display'
        }  # Don't send distant_display to the db

        delay = .5
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                response = requests.post(
                    server_url + "/iot/setup",
                    json={'params': {'iot_box': iot_box, 'devices': devices_list_to_send}},
                    timeout=5,
                )
                response.raise_for_status()
                data = response.json()
                self.ws_channel = data.get('result', '')
                break  # Success, exit the retry loop
            except requests.exceptions.RequestException:
                if attempt < max_retries:
                    _logger.warning(
                        'Could not reach configured server to send all IoT devices, retrying in %s seconds (%d/%d attempts)',
                        delay, attempt, max_retries, exc_info=True
                    )
                    time.sleep(delay)
                else:
                    _logger.exception('Could not reach configured server to send all IoT devices after %d attempts.', max_retries)
            except ValueError:
                _logger.exception('Could not load JSON data: Received data is not valid JSON.\nContent:\n%s', response.content)
                break

    def run(self):
        """Thread that will load interfaces and drivers and contact the odoo server
        with the updates. It will also reconnect to the Wi-Fi if the connection is lost.
        """
        if IS_RPI:
            # ensure that the root filesystem is writable retro compatibility (TODO: remove this in 19.0)
            subprocess.run(["sudo", "mount", "-o", "remount,rw", "/"], check=False)
            subprocess.run(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/"], check=False)

            wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))

        helpers.start_nginx_server()
        _logger.info("IoT Box Image version: %s", helpers.get_version(detailed_version=True))
        upgrade.check_git_branch()

        if IS_RPI and helpers.get_odoo_server_url():
            helpers.generate_password()

        certificate.ensure_validity()

        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self._send_all_devices()
        helpers.download_iot_handlers()
        helpers.load_iot_handlers()

        for interface in interfaces.values():
            interface().start()

        # Set scheduled actions
        schedule.every().day.at("00:00").do(certificate.ensure_validity)
        schedule.every().day.at("00:00").do(helpers.reset_log_level)

        # Set up the websocket connection
        ws_client = WebsocketClient(self.ws_channel)
        if ws_client:
            ws_client.start()

        # Check every 3 seconds if the list of connected devices has changed and send the updated
        # list to the connected DB.
        while 1:
            try:
                if self._get_changes_to_send():
                    self._send_all_devices()
                if IS_RPI and helpers.get_ip() != '10.11.12.1':
                    wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))
                time.sleep(3)
                schedule.run_pending()
            except Exception:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.exception("Manager loop unexpected error")


manager = Manager()
manager.start()
