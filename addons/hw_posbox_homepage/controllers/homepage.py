# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import netifaces
import os
import platform
import subprocess
import threading
import time

from itertools import groupby
from pathlib import Path
from odoo import http
from odoo.addons.hw_drivers.tools import helpers, wifi
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

CONTENT_SECURITY_POLICY = (
    "default-src 'none';"
    "script-src 'self' 'unsafe-eval';"  # OWL requires `unsafe-eval` to render templates
    "connect-src 'self';"
    "img-src 'self' data:;"             # `data:` scheme required as Bootstrap uses it for embedded SVGs
    "style-src 'self';"
    "font-src 'self';"
)


class IotBoxOwlHomePage(http.Controller):
    def __init__(self):
        super().__init__()
        self.updating = threading.Lock()

    @http.route('/', auth='none', type='http')
    def index(self):
        return http.Stream.from_path("hw_posbox_homepage/views/index.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

    @http.route('/logs', auth='none', type='http')
    def logs_page(self):
        return http.Stream.from_path("hw_posbox_homepage/views/logs.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

    @http.route('/status', auth='none', type='http')
    def status_page(self):
        return http.Stream.from_path("hw_posbox_homepage/views/status_display.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

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

    @http.route('/hw_posbox_homepage/iot_logs', auth='none', type='http', cors='*')
    def get_iot_logs(self):
        with open("/var/log/odoo/odoo-server.log", encoding="utf-8") as file:
            return json.dumps({
                'status': 'success',
                'logs': file.read(),
            })

    @http.route('/hw_posbox_homepage/six_payment_terminal_clear', auth='none', type='http', cors='*')
    def clear_six_terminal(self):
        helpers.update_conf({'six_payment_terminal': ''})
        return json.dumps({
            'status': 'success',
            'message': 'Successfully cleared Six Payment Terminal',
        })

    @http.route('/hw_posbox_homepage/clear_credential', auth='none', type='http', cors='*')
    def clear_credential(self):
        helpers.update_conf({
            'db_uuid': '',
            'enterprise_code': '',
        })
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'Successfully cleared credentials',
        })

    @http.route('/hw_posbox_homepage/wifi_clear', auth='none', type='http', cors='*')
    def clear_wifi_configuration(self):
        helpers.update_conf({'wifi_ssid': '', 'wifi_password': ''})
        wifi.disconnect(forget_network=True)
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
    def get_homepage_data(self):
        network_interfaces = []
        if platform.system() == 'Linux':
            ssid = wifi.get_current() or wifi.get_access_point_ssid()
            interfaces = netifaces.interfaces()
            for iface_id in interfaces:
                if 'wlan' in iface_id or 'eth' in iface_id:
                    is_wifi = 'wlan' in iface_id
                    iface_obj = netifaces.ifaddresses(iface_id)
                    ifconfigs = iface_obj.get(netifaces.AF_INET, [])
                    for conf in ifconfigs:
                        if conf.get('addr'):
                            network_interfaces.append({
                                'id': iface_id,
                                'is_wifi': is_wifi,
                                'ssid': ssid if is_wifi else None,
                                'ip': conf.get('addr'),
                            })

        is_certificate_ok, certificate_details = helpers.get_certificate_status()

        devices = [{
            'name': device.device_name,
            'value': str(device.data['value']),
            'type': device.device_type,
            'identifier': device.device_identifier
        } for device in iot_devices.values()]
        device_type_key = lambda device: device['type']
        grouped_devices = {
            device_type: list(devices) for device_type, devices in groupby(sorted(devices, key=device_type_key), device_type_key)
        }

        terminal_id = helpers.get_conf('six_payment_terminal')
        six_terminal = terminal_id or 'Not Configured'

        return json.dumps({
            'db_uuid': helpers.get_conf('db_uuid'),
            'enterprise_code': helpers.get_conf('enterprise_code'),
            'hostname': helpers.get_hostname(),
            'ip': helpers.get_ip(),
            'mac': helpers.get_mac_address(),
            'devices': grouped_devices,
            'server_status': helpers.get_odoo_server_url() or 'Not Configured',
            'pairing_code': connection_manager.pairing_code,
            'six_terminal': six_terminal,
            'is_access_point_up': platform.system() == 'Linux' and wifi.is_access_point(),
            'network_interfaces': network_interfaces,
            'version': helpers.get_version(),
            'system': platform.system(),
            'is_certificate_ok': is_certificate_ok,
            'certificate_details': certificate_details,
        })

    @http.route('/hw_posbox_homepage/wifi', auth="none", type="http", cors='*')
    def get_available_wifi(self):
        return json.dumps({
            'currentWiFi': wifi.get_current(),
            'availableWiFi': wifi.get_available_ssids(),
        })

    @http.route('/hw_posbox_homepage/generate_password', auth="none", type="http", cors='*')
    def generate_password(self):
        return json.dumps({
            'password': helpers.generate_password(),
        })

    @http.route('/hw_posbox_homepage/version_info', auth="none", type="http", cors='*')
    def get_version_info(self):
        git = ["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git"]
        # Check branch name and last commit hash on IoT Box
        current_commit = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, check=False, text=True)
        current_branch = subprocess.run(
            [*git, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, check=False, text=True
        )
        if current_commit.returncode != 0 or current_branch.returncode != 0:
            return
        current_commit = current_commit.stdout.strip()
        current_branch = current_branch.stdout.strip()

        last_available_commit = subprocess.run(
            [*git, "ls-remote", "origin", current_branch], capture_output=True, check=False, text=True
        )
        if last_available_commit.returncode != 0:
            _logger.error("Failed to retrieve last commit available for branch origin/%s", current_branch)
            return
        last_available_commit = last_available_commit.stdout.split()[0].strip()

        return json.dumps({
            'status': 'success',
            # Checkout requires db to align with its version (=branch)
            'odooIsUpToDate': current_commit == last_available_commit or not bool(helpers.get_odoo_server_url()),
            'imageIsUpToDate': not bool(helpers.check_image()),
            'currentCommitHash': current_commit,
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
    @http.route('/hw_posbox_homepage/six_payment_terminal_add', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def add_six_terminal(self, terminal_id):
        if terminal_id.isdigit():
            helpers.update_conf({'six_payment_terminal': terminal_id})
        else:
            _logger.warning('Ignoring invalid Six TID: "%s". Only digits are allowed', terminal_id)
            return self.clear_six_terminal()
        return {
            'status': 'success',
            'message': 'Successfully saved Six Payment Terminal',
        }

    @http.route('/hw_posbox_homepage/save_credential', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def save_credential(self, db_uuid, enterprise_code):
        helpers.update_conf({
            'db_uuid': db_uuid,
            'enterprise_code': enterprise_code,
        })
        helpers.odoo_restart(0)
        return {
            'status': 'success',
            'message': 'Successfully saved credentials',
        }

    @http.route('/hw_posbox_homepage/update_wifi', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def update_wifi(self, essid, password):
        if wifi.connect(essid, password):
            helpers.update_conf({'wifi_ssid': essid, 'wifi_password': password})
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

    @http.route('/hw_posbox_homepage/enable_ngrok', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def enable_remote_connection(self, auth_token):
        if subprocess.call(['pgrep', 'ngrok']) == 1:
            subprocess.Popen(['sudo', 'systemd-run', 'ngrok', 'tcp', '--authtoken', auth_token, '--log', '/tmp/ngrok.log', '22'])

        return {
            'status': 'success',
            'auth_token': auth_token,
            'message': 'Ngrok tunnel is now enabled',
        }

    @http.route('/hw_posbox_homepage/connect_to_server', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def connect_to_odoo_server(self, token=False, iotname=False):
        if token:
            try:
                if len(token.split('|')) == 4:
                    # Old style token with pipe separators (pre v18 DB)
                    url, token, db_uuid, enterprise_code = token.split('|')
                    configuration = helpers.parse_url(url)
                    helpers.save_conf_server(configuration["url"], token, db_uuid, enterprise_code)
                else:
                    # New token using query params (v18+ DB)
                    configuration = helpers.parse_url(token)
                    helpers.save_conf_server(**configuration)
            except ValueError:
                _logger.warning("Wrong server token: %s", token)
                return {
                    'status': 'failure',
                    'message': 'Invalid URL provided.',
                }
            except (subprocess.CalledProcessError, OSError, Exception):
                return {
                    'status': 'failure',
                    'message': 'Failed to write server configuration files on IoT. Please try again.',
                }

        if iotname and platform.system() == 'Linux' and iotname != helpers.get_hostname():
            subprocess.run([file_path(
                'iot_box_image/configuration/rename_iot.sh'), iotname], check=False)

        # 1 sec delay for IO operations (save_conf_server)
        helpers.odoo_restart(1)
        return {
            'status': 'success',
            'message': 'Successfully connected to db, IoT will restart to update the configuration.',
        }

    @http.route('/hw_posbox_homepage/log_levels_update', auth="none", type="jsonrpc", methods=['POST'], cors='*')
    def update_log_level(self, name, value):
        if not name.startswith(IOT_LOGGING_PREFIX) and name != 'log-to-server':
            return {
                'status': 'error',
                'message': 'Invalid logger name',
            }

        if name == 'log-to-server':
            check_and_update_odoo_config_log_to_server_option(value)

        name = name[len(IOT_LOGGING_PREFIX):]
        if name == 'root':
            self._update_logger_level('', value, AVAILABLE_LOG_LEVELS)
        elif name == 'odoo':
            self._update_logger_level('odoo', value, AVAILABLE_LOG_LEVELS)
            self._update_logger_level('werkzeug', value if value != 'debug' else 'info', AVAILABLE_LOG_LEVELS)
        elif name.startswith(INTERFACE_PREFIX):
            logger_name = name[len(INTERFACE_PREFIX):]
            self._update_logger_level(logger_name, value, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'interfaces')
        elif name.startswith(DRIVER_PREFIX):
            logger_name = name[len(DRIVER_PREFIX):]
            self._update_logger_level(logger_name, value, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'drivers')
        else:
            _logger.warning('Unhandled iot logger: %s', name)

        return {
            'status': 'success',
            'message': 'Logger level updated',
        }

    @http.route('/hw_posbox_homepage/update_git_tree', auth="none", type="json", methods=['POST'], cors='*')
    def update_git_tree(self):
        helpers.check_git_branch()
        return {
            'status': 'success',
            'message': 'Successfully updated the IoT Box',
        }

    # ---------------------------------------------------------- #
    # Utils                                                      #
    # ---------------------------------------------------------- #
    def _get_iot_handlers_logger(self, handlers_name, iot_handler_folder_name):
        handlers_loggers_level = dict()
        for handler_name in handlers_name:
            handler_logger = self._get_iot_handler_logger(handler_name, iot_handler_folder_name)
            if not handler_logger:
                # Might happen if the file didn't define a logger (or not init yet)
                handlers_loggers_level[handler_name] = False
                _logger.debug('Unable to find logger for handler %s', handler_name)
                continue
            logger_parent = handler_logger.parent
            handlers_loggers_level[handler_name] = {
                'level': self._get_logger_effective_level_str(handler_logger),
                'is_using_parent_level': handler_logger.level == logging.NOTSET,
                'parent_name': logger_parent.name,
                'parent_level': self._get_logger_effective_level_str(logger_parent),
            }
        return handlers_loggers_level

    def _update_logger_level(self, logger_name, new_level, available_log_levels, handler_folder=False):
        """Update (if necessary) Odoo's configuration and logger to the given logger_name to the given level.
        The responsibility of saving the config file is not managed here.

        :param logger_name: name of the logging logger to change level
        :param new_level: new log level to set for this logger
        :param available_log_levels: iterable of logs levels allowed (for initial check)
        :param str handler_folder: optional string of the IoT handler folder name ('interfaces' or 'drivers')
        """
        # We store the timestamp to reset the log level to warning after a week (7 days * 24 hours * 3600 seconds)
        # This is to avoid sending polluted logs with debug messages to the db
        conf = {'log_level_reset_timestamp': str(time.time() + 7 * 24 * 3600)}

        if new_level not in available_log_levels:
            _logger.warning('Unknown level to set on logger %s: %s', logger_name, new_level)
            return

        if handler_folder:
            logger = self._get_iot_handler_logger(logger_name, handler_folder)
            if not logger:
                _logger.warning('Unable to change log level for logger %s as logger missing', logger_name)
                return
            logger_name = logger.name

        ODOO_TOOL_CONFIG_HANDLER_NAME = 'log_handler'
        LOG_HANDLERS = (helpers.get_conf(ODOO_TOOL_CONFIG_HANDLER_NAME, section='options') or []).split(',')
        LOGGER_PREFIX = logger_name + ':'
        IS_NEW_LEVEL_PARENT = new_level == 'parent'

        if not IS_NEW_LEVEL_PARENT:
            intended_to_find = LOGGER_PREFIX + new_level.upper()
            if intended_to_find in LOG_HANDLERS:
                # There is nothing to do, the entry is already inside
                return

        # We remove every occurrence for the given logger
        log_handlers_without_logger = [
            log_handler for log_handler in LOG_HANDLERS if not log_handler.startswith(LOGGER_PREFIX)
        ]

        if IS_NEW_LEVEL_PARENT:
            # We must check that there is no existing entries using this logger (whatever the level)
            if len(log_handlers_without_logger) == len(LOG_HANDLERS):
                return

        # We add if necessary new logger entry
        # If it is "parent" it means we want it to inherit from the parent logger.
        # In order to do this we have to make sure that no entries for the logger exists in the
        # `log_handler` (which is the case at this point as long as we don't re-add an entry)
        new_level_upper_case = new_level.upper()
        if not IS_NEW_LEVEL_PARENT:
            new_entry = LOGGER_PREFIX + new_level_upper_case
            log_handlers_without_logger.append(new_entry)
            _logger.debug('Adding to odoo config log_handler: %s', new_entry)
        conf[ODOO_TOOL_CONFIG_HANDLER_NAME] = ','.join(log_handlers_without_logger)

        # Update the logger dynamically
        real_new_level = logging.NOTSET if IS_NEW_LEVEL_PARENT else new_level_upper_case
        _logger.debug('Change logger %s level to %s', logger_name, real_new_level)
        logging.getLogger(logger_name).setLevel(real_new_level)

        helpers.update_conf(conf, section='options')

    def _get_logger_effective_level_str(self, logger):
        return logging.getLevelName(logger.getEffectiveLevel()).lower()

    def _get_iot_handler_logger(self, handler_name, handler_folder_name):
        """
        Get Odoo Iot logger given an IoT handler name
        :param handler_name: name of the IoT handler
        :param handler_folder_name: IoT handler folder name (interfaces or drivers)
        :return: logger if any, False otherwise
        """
        odoo_addon_handler_path = helpers.compute_iot_handlers_addon_name(handler_folder_name, handler_name)
        return odoo_addon_handler_path in logging.Logger.manager.loggerDict and \
               logging.getLogger(odoo_addon_handler_path)
