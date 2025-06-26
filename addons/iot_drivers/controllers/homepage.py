# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import netifaces
import requests
import subprocess
import threading
import time

from itertools import groupby
from pathlib import Path

from odoo import http
from odoo.addons.iot_drivers.tools import certificate, helpers, route, upgrade, wifi
from odoo.addons.iot_drivers.tools.system import IOT_SYSTEM, IS_RPI
from odoo.addons.iot_drivers.main import iot_devices, unsupported_devices
from odoo.addons.iot_drivers.connection_manager import connection_manager
from odoo.tools.misc import file_path
from odoo.addons.iot_drivers.server_logger import (
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

    @route.iot_route('/', type='http')
    def index(self):
        return http.Stream.from_path("iot_drivers/views/index.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

    @route.iot_route('/logs', type='http')
    def logs_page(self):
        return http.Stream.from_path("iot_drivers/views/logs.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

    @route.iot_route('/status', type='http')
    def status_page(self):
        return http.Stream.from_path("iot_drivers/views/status_display.html").get_response(content_security_policy=CONTENT_SECURITY_POLICY)

    # ---------------------------------------------------------- #
    # GET methods                                                #
    # -> Always use json.dumps() to return a JSON response       #
    # ---------------------------------------------------------- #
    @route.iot_route('/iot_drivers/restart_odoo_service', type='http', cors='*')
    def odoo_service_restart(self):
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'Odoo service restarted',
        })

    @route.iot_route('/iot_drivers/iot_logs', type='http', cors='*')
    def get_iot_logs(self):
        logs_path = "/var/log/odoo/odoo-server.log" if IS_RPI else Path().absolute().parent.joinpath('odoo.log')
        with open(logs_path, encoding="utf-8") as file:
            return json.dumps({
                'status': 'success',
                'logs': file.read(),
            })

    @route.iot_route('/iot_drivers/six_payment_terminal_clear', type='http', cors='*')
    def clear_six_terminal(self):
        helpers.update_conf({'six_payment_terminal': ''})
        return json.dumps({
            'status': 'success',
            'message': 'Successfully cleared Six Payment Terminal',
        })

    @route.iot_route('/iot_drivers/clear_credential', type='http', cors='*')
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

    @route.iot_route('/iot_drivers/wifi_clear', type='http', cors='*', linux_only=True)
    def clear_wifi_configuration(self):
        helpers.update_conf({'wifi_ssid': '', 'wifi_password': ''})
        wifi.disconnect()
        return json.dumps({
            'status': 'success',
            'message': 'Successfully disconnected from wifi',
        })

    @route.iot_route('/iot_drivers/server_clear', type='http', cors='*')
    def clear_server_configuration(self):
        helpers.disconnect_from_server()
        close_server_log_sender_handler()
        return json.dumps({
            'status': 'success',
            'message': 'Successfully disconnected from server',
        })

    @route.iot_route('/iot_drivers/ping', type='http', cors='*')
    def ping(self):
        return json.dumps({
            'status': 'success',
            'message': 'pong',
        })

    @route.iot_route('/iot_drivers/data', type="http", cors='*')
    def get_homepage_data(self):
        network_interfaces = []
        if IS_RPI:
            ssid = wifi.get_current() or wifi.get_access_point_ssid()
            for iface_id in netifaces.interfaces():
                if iface_id == 'lo':
                    continue  # Skip loopback interface (127.0.0.1)

                is_wifi = 'wlan' in iface_id
                network_interfaces.extend([{
                    'id': iface_id,
                    'is_wifi': is_wifi,
                    'ssid': ssid if is_wifi else None,
                    'ip': conf.get('addr', 'No Internet'),
                } for conf in netifaces.ifaddresses(iface_id).get(netifaces.AF_INET, [])])

        devices = [{
            'name': device.device_name,
            'value': str(device.data['value']),
            'type': device.device_type,
            'identifier': device.device_identifier,
            'connection': device.device_connection,
        } for device in iot_devices.values()]
        devices += list(unsupported_devices.values())

        def device_type_key(device):
            return device['type']

        grouped_devices = {
            device_type: list(devices)
            for device_type, devices in groupby(sorted(devices, key=device_type_key), device_type_key)
        }

        six_terminal = helpers.get_conf('six_payment_terminal') or 'Not Configured'
        network_qr_codes = wifi.generate_network_qr_codes() if IS_RPI else {}
        odoo_server_url = helpers.get_odoo_server_url() or ''
        odoo_uptime_seconds = time.monotonic() - helpers.odoo_start_time
        system_uptime_seconds = time.monotonic() - helpers.system_start_time

        return json.dumps({
            'db_uuid': helpers.get_conf('db_uuid'),
            'enterprise_code': helpers.get_conf('enterprise_code'),
            'ip': helpers.get_ip(),
            'identifier': helpers.get_identifier(),
            'devices': grouped_devices,
            'server_status': odoo_server_url,
            'pairing_code': connection_manager.pairing_code,
            'new_database_url': connection_manager.new_database_url,
            'pairing_code_expired': connection_manager.pairing_code_expired and not odoo_server_url,
            'six_terminal': six_terminal,
            'is_access_point_up': IS_RPI and wifi.is_access_point(),
            'network_interfaces': network_interfaces,
            'version': helpers.get_version(),
            'system': IOT_SYSTEM,
            'odoo_uptime_seconds': odoo_uptime_seconds,
            'system_uptime_seconds': system_uptime_seconds,
            'certificate_end_date': certificate.get_certificate_end_date(),
            'wifi_ssid': helpers.get_conf('wifi_ssid'),
            'qr_code_wifi': network_qr_codes.get('qr_wifi'),
            'qr_code_url': network_qr_codes.get('qr_url'),
        })

    @route.iot_route('/iot_drivers/wifi', type="http", cors='*', linux_only=True)
    def get_available_wifi(self):
        return json.dumps({
            'currentWiFi': wifi.get_current(),
            'availableWiFi': wifi.get_available_ssids(),
        })

    @route.iot_route('/iot_drivers/version_info', type="http", cors='*', linux_only=True)
    def get_version_info(self):
        # Check branch name and last commit hash on IoT Box
        current_commit = upgrade.git("rev-parse", "HEAD")
        current_branch = upgrade.git("rev-parse", "--abbrev-ref", "HEAD")
        if not current_commit or not current_branch:
            return json.dumps({
                'status': 'error',
                'message': 'Failed to retrieve current commit or branch',
            })

        last_available_commit = upgrade.git("ls-remote", "origin", current_branch)
        if not last_available_commit:
            _logger.error("Failed to retrieve last commit available for branch origin/%s", current_branch)
            return json.dumps({
                'status': 'error',
                'message': 'Failed to retrieve last commit available for branch origin/' + current_branch,
            })
        last_available_commit = last_available_commit.split()[0].strip()

        return json.dumps({
            'status': 'success',
            # Checkout requires db to align with its version (=branch)
            'odooIsUpToDate': current_commit == last_available_commit or not bool(helpers.get_odoo_server_url()),
            'imageIsUpToDate': IS_RPI and not bool(helpers.check_image()),
            'currentCommitHash': current_commit,
        })

    @route.iot_route('/iot_drivers/log_levels', type="http", cors='*')
    def log_levels(self):
        drivers_list = helpers.get_handlers_files_to_load(
            file_path('iot_drivers/iot_handlers/drivers'))
        interfaces_list = helpers.get_handlers_files_to_load(
            file_path('iot_drivers/iot_handlers/interfaces'))
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

    @route.iot_route('/iot_drivers/load_iot_handlers', type="http", cors='*')
    def load_iot_handlers(self):
        helpers.download_iot_handlers(False)
        helpers.odoo_restart(0)
        return json.dumps({
            'status': 'success',
            'message': 'IoT Handlers loaded successfully',
        })

    @route.iot_route('/iot_drivers/is_ngrok_enabled', type="http", linux_only=True)
    def is_ngrok_enabled(self):
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            response.raise_for_status()
            response.json()
        except (requests.exceptions.RequestException, ValueError):
            # if the request fails or the response is not valid JSON,
            # it means ngrok is not enabled or not running
            return json.dumps({'enabled': False})

        return json.dumps({'enabled': True})

    # ---------------------------------------------------------- #
    # POST methods                                               #
    # -> Never use json.dumps() it will be done automatically    #
    # ---------------------------------------------------------- #
    @route.iot_route('/iot_drivers/six_payment_terminal_add', type="jsonrpc", methods=['POST'], cors='*')
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

    @route.iot_route('/iot_drivers/save_credential', type="jsonrpc", methods=['POST'], cors='*')
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

    @route.iot_route('/iot_drivers/update_wifi', type="jsonrpc", methods=['POST'], cors='*', linux_only=True)
    def update_wifi(self, essid, password):
        if wifi.reconnect(essid, password, force_update=True):
            helpers.update_conf({'wifi_ssid': essid, 'wifi_password': password})

            res_payload = {
                'status': 'success',
                'message': 'Connecting to ' + essid,
            }
        else:
            res_payload = {
                'status': 'error',
                'message': 'Failed to connect to ' + essid,
            }

        return res_payload

    @route.iot_route(
        '/iot_drivers/generate_password', type="jsonrpc", methods=["POST"], cors='*', linux_only=True
    )
    def generate_password(self):
        return {
            'password': helpers.generate_password(),
        }

    @route.iot_route('/iot_drivers/enable_ngrok', type="jsonrpc", methods=['POST'], linux_only=True)
    def enable_remote_connection(self, auth_token):
        p = subprocess.run(
            ['ngrok', 'config', 'add-authtoken', auth_token, '--config', '/home/pi/ngrok.yml'],
            check=False,
        )
        if p.returncode == 0:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', 'odoo-ngrok.service'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return {'status': 'success'}

        return {'status': 'failure'}

    @route.iot_route('/iot_drivers/disable_ngrok', type="jsonrpc", methods=['POST'], linux_only=True)
    def disable_remote_connection(self):
        p = subprocess.run(
            ['ngrok', 'config', 'add-authtoken', '""', '--config', '/home/pi/ngrok.yml'], check=False
        )
        if p.returncode == 0:
            subprocess.run(
                ['sudo', 'systemctl', 'stop', 'odoo-ngrok.service'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            return {'status': 'success'}

        return {'status': 'failure'}

    @route.iot_route('/iot_drivers/connect_to_server', type="jsonrpc", methods=['POST'], cors='*')
    def connect_to_odoo_server(self, token):
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

        # 1 sec delay for IO operations (save_conf_server)
        helpers.odoo_restart(1)
        return {
            'status': 'success',
            'message': 'Successfully connected to db, IoT will restart to update the configuration.',
        }

    @route.iot_route('/iot_drivers/log_levels_update', type="jsonrpc", methods=['POST'], cors='*')
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

    @route.iot_route('/iot_drivers/update_git_tree', type="jsonrpc", methods=['POST'], cors='*', linux_only=True)
    def update_git_tree(self):
        upgrade.check_git_branch()
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
