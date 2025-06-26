# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import schedule
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

    @helpers.require_db
    def send_all_devices(self, server_url=None):
        """This method send IoT Box and devices information to Odoo database

        :param server_url: URL of the Odoo server (provided by decorator).
        """
        subject = helpers.get_conf('subject')
        if subject:
            domain = helpers.get_ip().replace('.', '-') + subject.strip('*')
        else:
            domain = helpers.get_ip()
        iot_box = {
            'name': helpers.get_hostname(),
            'identifier': helpers.get_identifier(),
            'ip': domain,
            'token': helpers.get_token(),
            'version': helpers.get_version(detailed_version=True),
        }
        devices_list = {}
        for iot_device in iot_devices.values():
            identifier = iot_device.device_identifier
            devices_list[identifier] = {
                'name': iot_device.device_name,
                'type': iot_device.device_type,
                'manufacturer': iot_device.device_manufacturer,
                'connection': iot_device.device_connection,
                'subtype': iot_device.device_subtype if iot_device.device_type == 'printer' else '',
            }
        devices_list.update(unsupported_devices)
        devices_list_to_send = {
            key: value for key, value in devices_list.items() if key != 'distant_display'
        }  # Don't send distant_display to the db
        try:
            response = requests.post(
                server_url + "/iot/setup",
                json={'params': {'iot_box': iot_box, 'devices': devices_list_to_send}},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()

            self.ws_channel = data.get('result', '')
        except requests.exceptions.RequestException:
            _logger.exception('Could not reach configured server to send all IoT devices')
        except ValueError:
            _logger.exception('Could not load JSON data: Received data is not valid JSON.\nContent:\n%s', response.content)

    def run(self):
        """Thread that will load interfaces and drivers and contact the odoo server
        with the updates. It will also reconnect to the Wi-Fi if the connection is lost.
        """
        if IS_RPI:
            wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))

        helpers.start_nginx_server()
        _logger.info("IoT Box Image version: %s", helpers.get_version(detailed_version=True))
        upgrade.check_git_branch()

        if IS_RPI and helpers.get_odoo_server_url():
            helpers.generate_password()

        certificate.ensure_validity()

        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self.send_all_devices()
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
        previous_iot_devices = set()
        while 1:
            try:
                current_devices = set(iot_devices.keys()) | set(unsupported_devices.keys())
                if current_devices != previous_iot_devices:
                    previous_iot_devices = current_devices
                    self.send_all_devices()
                if IS_RPI and helpers.get_ip() != '10.11.12.1':
                    wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))
                time.sleep(3)
                schedule.run_pending()
            except Exception:
                # No matter what goes wrong, the Manager loop needs to keep running
                _logger.exception("Manager loop unexpected error")


manager = Manager()
manager.start()
