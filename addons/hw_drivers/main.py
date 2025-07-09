# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import platform
import logging
import requests
from threading import Thread
import time

from odoo.addons.hw_drivers.tools import helpers, wifi
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
    ws_channel = ""

<<<<<<< 037d10377398b55f03e38ba82f103171ed5bb94f
    @helpers.require_db
    def send_all_devices(self, server_url=None):
        """This method send IoT Box and devices information to Odoo database

        :param server_url: URL of the Odoo server (provided by decorator).
||||||| 00a9e2d19cdb8d7d4938f341b6a2e85811a7367d
    def send_alldevices(self, iot_client=None):
=======
    def __init__(self):
        super().__init__()
        self.hostname = helpers.get_hostname()
        self.mac_address = helpers.get_mac_address()
        self.domain = self._get_domain()
        self.token = helpers.get_token()
        self.version = helpers.get_version(detailed_version=True)
        self.previous_iot_devices = {}

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
>>>>>>> 6c3afeb9dfe046d47de978e1f54d7689def66d4a
        """
<<<<<<< 037d10377398b55f03e38ba82f103171ed5bb94f
        subject = helpers.get_conf('subject')
        if subject:
            domain = helpers.get_ip().replace('.', '-') + subject.strip('*')
||||||| 00a9e2d19cdb8d7d4938f341b6a2e85811a7367d
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
=======
        This method send IoT Box and devices information to Odoo database
        """
        if self.server_url:
            iot_box = {
                'name': self.hostname,
                'identifier': self.mac_address,
                'ip': self.domain,
                'token': self.token,
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
>>>>>>> 6c3afeb9dfe046d47de978e1f54d7689def66d4a
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
        if platform.system() == 'Linux':
            wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))

        helpers.start_nginx_server()

        _logger.info("IoT Box Image version: %s", helpers.get_version(detailed_version=True))
        if platform.system() == 'Linux' and helpers.get_odoo_server_url():
            helpers.check_git_branch()
            helpers.generate_password()
        is_certificate_ok, certificate_details = helpers.get_certificate_status()
        if not is_certificate_ok and certificate_details != 'ERR_IOT_HTTPS_CHECK_NO_SERVER':
            _logger.warning("An error happened when trying to get the HTTPS certificate: %s",
                            certificate_details)

        # We first add the IoT Box to the connected DB because IoT handlers cannot be downloaded if
        # the identifier of the Box is not found in the DB. So add the Box to the DB.
        self.send_all_devices()
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
        schedule and schedule.every().day.at("00:00").do(helpers.get_certificate_status)
        schedule and schedule.every().day.at("00:00").do(helpers.reset_log_level)

        # Set up the websocket connection
        ws_client = WebsocketClient(self.ws_channel)
        if ws_client:
            ws_client.start()

        # Check every 3 seconds if the list of connected devices has changed and send the updated
        # list to the connected DB.
        previous_iot_devices = []
        while 1:
            try:
<<<<<<< 037d10377398b55f03e38ba82f103171ed5bb94f
                if iot_devices != previous_iot_devices:
                    previous_iot_devices = iot_devices.copy()
                    self.send_all_devices()
                if platform.system() == 'Linux' and helpers.get_ip() != '10.11.12.1':
                    wifi.reconnect(helpers.get_conf('wifi_ssid'), helpers.get_conf('wifi_password'))
||||||| 00a9e2d19cdb8d7d4938f341b6a2e85811a7367d
                if iot_devices != self.previous_iot_devices:
                    self.previous_iot_devices = iot_devices.copy()
                    self.send_alldevices(iot_client)
=======
                if self._get_changes_to_send():
                    self.send_alldevices(iot_client)
>>>>>>> 6c3afeb9dfe046d47de978e1f54d7689def66d4a
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
