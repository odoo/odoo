# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import subprocess
import threading
import logging
import platform
import jinja2
import os
import sys

from pathlib import Path
from odoo import http, tools
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.main import IoTboxHomepage
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.tools.misc import file_path
from odoo.addons.hw_drivers.server_logger import (
    check_and_update_odoo_config_log_to_server_option,
    get_odoo_config_log_to_server_option,
    close_server_log_sender_handler,
)

_logger = logging.getLogger(__name__)

IOT_LOGGING_PREFIX = 'iot-logging-'
INTERFACE_PREFIX = 'interface-'
DRIVER_PREFIX = 'driver-'
AVAILABLE_LOG_LEVELS = ('debug', 'info', 'warning', 'error')
AVAILABLE_LOG_LEVELS_WITH_PARENT = AVAILABLE_LOG_LEVELS + ('parent',)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_posbox_homepage', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

index_template = jinja_env.get_template('index.html')


class IotBoxOwlHomePage(IoTboxHomepage):
    def __init__(self):
        super().__init__()
        self.updating = threading.Lock()

    @http.route()
    def index(self):
        return index_template.render()

    # ---------------------------------------------------------- #
    # GET methods                                                #
    # -> Always use json.dumps() to return a JSON response       #
    # ---------------------------------------------------------- #
    @http.route('/hw_posbox_homepage/restart_odoo_service', auth='none', type='http', cors='*')
    def odoo_service_restart(self):
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'Odoo service restarted',
        })

    @http.route('/hw_posbox_homepage/restart_iotbox', auth='none', type='http', cors='*')
    def iotbox_restart(self):
        subprocess.call(['sudo', 'reboot'])
        return json.dumps({
            'status': 'success',
            'message': 'IoT Box is restarting',
        })

    @http.route('/hw_posbox_homepage/iot_logs', auth='none', type='http', cors='*')
    def get_iot_logs(self):
        logs = open("/var/log/odoo/odoo-server.log", "r")
        return json.dumps({
            'status': 'success',
            'logs': logs.read(),
        })

    @http.route('/hw_posbox_homepage/six_payment_terminal_clear', auth='none', type='http', cors='*')
    def clear_six_terminal(self):
        helpers.unlink_file('odoo-six-payment-terminal.conf')
        return json.dumps({
            'status': 'success',
            'message': 'Successfully cleared Six Payment Terminal',
        })

    @http.route('/hw_posbox_homepage/clear_credential', auth='none', type='http', cors='*')
    def clear_credential(self):
        helpers.unlink_file('odoo-db-uuid.conf')
        helpers.unlink_file('odoo-enterprise-code.conf')
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'Successfully cleared credentials',
        })

    @http.route('/hw_posbox_homepage/wifi_clear', auth='none', type='http', cors='*')
    def clear_wifi_configuration(self):
        helpers.unlink_file('wifi_network.txt')
        return json.dumps({
            'status': 'success',
            'message': 'Successfully disconnected from wifi',
        })

    @http.route('/hw_posbox_homepage/server_clear', auth='none', type='http', cors='*')
    def clear_server_configuration(self):
        helpers.disconnect_from_server()
        close_server_log_sender_handler()
        return json.dumps({
            'status': 'success',
            'message': 'Successfully disconnected from server',
        })

    @http.route('/hw_posbox_homepage/ping', auth='none', type='http', cors='*')
    def ping(self):
        return json.dumps({
            'status': 'success',
            'message': 'pong',
        })

    @http.route('/hw_posbox_homepage/data', auth="none", type="http", cors='*')
    def get_homepage_data_new(self):
        if platform.system() == 'Linux':
            ssid = helpers.get_ssid()
            wired = helpers.read_file_first_line('/sys/class/net/eth0/operstate')
        else:
            wired = 'up'
        if wired == 'up':
            network = 'Ethernet'
        elif ssid:
            if helpers.access_point():
                network = 'Wifi access point'
            else:
                network = 'Wifi : ' + ssid
        else:
            network = 'Not Connected'

        is_certificate_ok, certificate_details = helpers.get_certificate_status()

        iot_device = []
        for device in iot_devices:
            iot_device.append({
                'name': iot_devices[device].device_name + ' : ' + str(iot_devices[device].data['value']),
                'type': iot_devices[device].device_type.replace('_', ' '),
                'identifier': iot_devices[device].device_identifier,
            })

        terminal_id = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
        six_terminal = terminal_id or 'Not Configured'

        return json.dumps({
            'db_uuid': helpers.read_file_first_line('odoo-db-uuid.conf'),
            'enterprise_code': helpers.read_file_first_line('odoo-enterprise-code.conf'),
            'hostname': helpers.get_hostname(),
            'ip': helpers.get_ip(),
            'mac': helpers.get_mac_address(),
            'iot_device_status': iot_device,
            'server_status': helpers.get_odoo_server_url() or 'Not Configured',
            'pairing_code': connection_manager.pairing_code,
            'six_terminal': six_terminal,
            'network_status': network,
            'version': helpers.get_version(),
            'system': platform.system(),
            'is_certificate_ok': is_certificate_ok,
            'certificate_details': certificate_details,
        })

    @http.route('/hw_posbox_homepage/wifi', auth="none", type="http", cors='*')
    def get_available_wifi(self):
        return json.dumps(helpers.get_wifi_essid())

    @http.route('/hw_posbox_homepage/generate_password', auth="none", type="http", cors='*')
    def generate_password(self):
        return json.dumps({
            'password': helpers.generate_password(),
        })

    @http.route('/hw_posbox_homepage/upgrade', auth="none", type="http", cors='*')
    def upgrade_iotbox(self):
        commit = subprocess.check_output(
            ["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git", "log", "-1"]).decode('utf-8').replace("\n", "<br/>")
        flashToVersion = helpers.check_image()
        actualVersion = helpers.get_version()

        if flashToVersion:
            flashToVersion = '%s.%s' % (flashToVersion.get(
                'major', ''), flashToVersion.get('minor', ''))

        return json.dumps({
            'title': "Odoo's IoTBox - Software Upgrade",
            'breadcrumb': 'IoT Box Software Upgrade',
            'loading_message': 'Updating IoT box',
            'commit': commit,
            'flashToVersion': flashToVersion,
            'actualVersion': actualVersion,
        })

    @http.route('/hw_posbox_homepage/log_levels', auth="none", type="http", cors='*')
    def log_levels(self):
        drivers_list = helpers.list_file_by_os(
            file_path('hw_drivers/iot_handlers/drivers'))
        interfaces_list = helpers.list_file_by_os(
            file_path('hw_drivers/iot_handlers/interfaces'))
        return json.dumps({
            'title': "Odoo's IoT Box - Handlers list",
            'breadcrumb': 'Handlers list',
            'drivers_list': drivers_list,
            'interfaces_list': interfaces_list,
            'server': helpers.get_odoo_server_url(),
            'is_log_to_server_activated': get_odoo_config_log_to_server_option(),
            'root_logger_log_level': self._get_logger_effective_level_str(logging.getLogger()),
            'odoo_current_log_level': self._get_logger_effective_level_str(logging.getLogger('odoo')),
            'recommended_log_level': 'warning',
            'available_log_levels': AVAILABLE_LOG_LEVELS,
            'drivers_logger_info': self._get_iot_handlers_logger(drivers_list, 'drivers'),
            'interfaces_logger_info': self._get_iot_handlers_logger(interfaces_list, 'interfaces'),
        })

    @http.route('/hw_posbox_homepage/load_iot_handlers', auth="none", type="http", cors='*')
    def load_iot_log_level(self):
        helpers.download_iot_handlers(False)
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'IoT Handlers loaded successfully',
        })

    @http.route('/hw_posbox_homepage/clear_iot_handlers', auth="none", type="http", cors='*')
    def clear_iot_handlers(self):
        for directory in ['drivers', 'interfaces']:
            for file in list(Path(file_path(f'hw_drivers/iot_handlers/{directory}')).glob('*')):
                if file.name != '__pycache__':
                    helpers.unlink_file(str(file.relative_to(*file.parts[:3])))

        return json.dumps({
            'status': 'success',
            'message': 'IoT Handlers cleared successfully',
        })

    # ---------------------------------------------------------- #
    # POST methods                                               #
    # -> Never use json.dumps() it will be done automatically    #
    # ---------------------------------------------------------- #
    @http.route('/hw_posbox_homepage/six_payment_terminal_add', auth="none", type="json", methods=['POST'], cors='*')
    def add_six_terminal(self, terminal_id):
        if terminal_id.isdigit():
            helpers.write_file('odoo-six-payment-terminal.conf', terminal_id)
        else:
            _logger.warning('Ignoring invalid Six TID: "%s". Only digits are allowed', terminal_id)
            return self.clear_six_terminal()
        return {
            'status': 'success',
            'message': 'Successfully saved Six Payment Terminal',
        }

    @http.route('/hw_posbox_homepage/save_credential', auth="none", type="json", methods=['POST'], cors='*')
    def save_credential(self, db_uuid, enterprise_code):
        helpers.write_file('odoo-db-uuid.conf', db_uuid)
        helpers.write_file('odoo-enterprise-code.conf', enterprise_code)
        helpers.odoo_restart(0)
        return {
            'status': 'success',
            'message': 'Successfully saved credentials',
        }

    @http.route('/hw_posbox_homepage/update_wifi', auth="none", type="json", methods=['POST'], cors='*')
    def update_wifi(self, essid, password, persistent=False):
        persistent = '1' if persistent else ''
        subprocess.check_call([file_path(
            'point_of_sale/tools/posbox/configuration/connect_to_wifi.sh'), essid, password, persistent])
        server = helpers.get_odoo_server_url()

        res_payload = {
            'status': 'success',
            'message': 'Connecting to ' + essid,
            'server': {
                'url': server or 'http://' + helpers.get_ip() + ':8069',
                'message': 'Redirect to Odoo Server' if server else 'Redirect to IoT Box'
            }
        }

        return res_payload

    @http.route('/hw_posbox_homepage/enable_ngrok', auth="none", type="json", methods=['POST'], cors='*')
    def enable_remote_connection(self, auth_token):
        if subprocess.call(['pgrep', 'ngrok']) == 1:
            subprocess.Popen(['ngrok', 'tcp', '--authtoken', auth_token, '--log', '/tmp/ngrok.log', '22'])

        return {
            'status': 'success',
            'auth_token': auth_token,
            'message': 'Ngrok tunnel is now enabled',
        }

    @http.route('/hw_posbox_homepage/connect_to_server', auth="none", type="json", methods=['POST'], cors='*')
    def connect_to_odoo_server(self, token=False, iotname=False):
        if token:
            credential = token.split('|')
            url = credential[0]
            token = credential[1]
            db_uuid = credential[2]
            enterprise_code = credential[3]
            try:
                helpers.save_conf_server(url, token, db_uuid, enterprise_code)
            except (subprocess.CalledProcessError, OSError, Exception):
                return 'Failed to write server configuration files on IoT. Please try again.'

        if iotname and platform.system() == 'Linux' and iotname != helpers.get_hostname():
            subprocess.run([file_path(
                'point_of_sale/tools/posbox/configuration/rename_iot.sh'), iotname], check=False)

        # 1 sec delay for IO operations (save_conf_server)
        helpers.odoo_restart(1)
        return {
            'status': 'success',
            'message': 'Successfully connected to db, IoT will restart to update the configuration.',
        }

    @http.route('/hw_posbox_homepage/log_levels_update', auth="none", type="json", methods=['POST'], cors='*')
    def update_log_level(self, name, value):
        if not name.startswith(IOT_LOGGING_PREFIX) and name != 'log-to-server':
            return {
                'status': 'error',
                'message': 'Invalid logger name',
            }

        need_config_save = False
        if name == 'log-to-server':
            need_config_save |= check_and_update_odoo_config_log_to_server_option(
                value
            )

        name = name[len(IOT_LOGGING_PREFIX):]
        if name == 'root':
            need_config_save |= self._update_logger_level(
                '', value, AVAILABLE_LOG_LEVELS)
        elif name == 'odoo':
            need_config_save |= self._update_logger_level(
                'odoo', value, AVAILABLE_LOG_LEVELS)
            need_config_save |= self._update_logger_level(
                'werkzeug', value if value != 'debug' else 'info', AVAILABLE_LOG_LEVELS)
        elif name.startswith(INTERFACE_PREFIX):
            logger_name = name[len(INTERFACE_PREFIX):]
            need_config_save |= self._update_logger_level(
                logger_name, value, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'interfaces')
        elif name.startswith(DRIVER_PREFIX):
            logger_name = name[len(DRIVER_PREFIX):]
            need_config_save |= self._update_logger_level(
                logger_name, value, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'drivers')
        else:
            _logger.warning('Unhandled iot logger: %s', name)

        if need_config_save:
            with helpers.writable():
                tools.config.save()

        return {
            'status': 'success',
            'message': 'Logger level updated',
        }
