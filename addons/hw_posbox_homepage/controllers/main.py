# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import jinja2
import platform
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading

from odoo import http, service, tools
from odoo.http import Response, request
from odoo.modules.module import get_resource_path
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_posbox_homepage', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

homepage_template = jinja_env.get_template('homepage.html')
server_config_template = jinja_env.get_template('server_config.html')
wifi_config_template = jinja_env.get_template('wifi_config.html')
handler_list_template = jinja_env.get_template('handler_list.html')
remote_connect_template = jinja_env.get_template('remote_connect.html')
configure_wizard_template = jinja_env.get_template('configure_wizard.html')
six_payment_terminal_template = jinja_env.get_template('six_payment_terminal.html')
list_credential_template = jinja_env.get_template('list_credential.html')
upgrade_page_template = jinja_env.get_template('upgrade_page.html')

class IoTboxHomepage(Home):
    def __init__(self):
        super(IoTboxHomepage,self).__init__()
        self.updating = threading.Lock()

    def clean_partition(self):
        subprocess.check_call(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; cleanup'])

    def get_six_terminal(self):
        terminal_id = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
        return terminal_id or 'Not Configured'

    def get_homepage_data(self):
        hostname = str(socket.gethostname())
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

        return {
            'hostname': hostname,
            'ip': helpers.get_ip(),
            'mac': helpers.get_mac_address(),
            'iot_device_status': iot_device,
            'server_status': helpers.get_odoo_server_url() or 'Not Configured',
            'pairing_code': connection_manager.pairing_code,
            'six_terminal': self.get_six_terminal(),
            'network_status': network,
            'version': helpers.get_version(),
            'system': platform.system(),
            'is_certificate_ok': is_certificate_ok,
            'certificate_details': certificate_details,
            }

    @http.route('/', type='http', auth='none')
    def index(self):
        wifi = Path.home() / 'wifi_network.txt'
        remote_server = Path.home() / 'odoo-remote-server.conf'
        if (wifi.exists() == False or remote_server.exists() == False) and helpers.access_point():
            return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069/steps'>"
        else:
            return homepage_template.render(self.get_homepage_data())

    @http.route('/list_handlers', type='http', auth='none', website=True, csrf=False, save_session=False)
    def list_handlers(self, **post):
        AVAILABLE_LOG_LEVELS = ('debug', 'info', 'warning', 'error')
        if request.httprequest.method == 'POST':
            IOT_LOGGING_PREFIX = 'iot-logging-'
            INTERFACE_PREFIX = 'interface-'
            DRIVER_PREFIX = 'driver-'
            AVAILABLE_LOG_LEVELS_WITH_PARENT = AVAILABLE_LOG_LEVELS + ('parent',)
            need_config_save = False
            for post_request_key, log_level_or_parent in post.items():
                if not post_request_key.startswith(IOT_LOGGING_PREFIX):
                    # probably a new post request payload argument not related to logging
                    continue
                post_request_key = post_request_key[len(IOT_LOGGING_PREFIX):]

                if post_request_key == 'root':
                    need_config_save |= self._update_logger_level('', log_level_or_parent, AVAILABLE_LOG_LEVELS)
                elif post_request_key == 'odoo':
                    need_config_save |= self._update_logger_level('odoo', log_level_or_parent, AVAILABLE_LOG_LEVELS)
                    need_config_save |= self._update_logger_level('werkzeug', log_level_or_parent if log_level_or_parent != 'debug' else 'info', AVAILABLE_LOG_LEVELS)
                elif post_request_key.startswith(INTERFACE_PREFIX):
                    logger_name = post_request_key[len(INTERFACE_PREFIX):]
                    need_config_save |= self._update_logger_level(logger_name, log_level_or_parent, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'interfaces')
                elif post_request_key.startswith(DRIVER_PREFIX):
                    logger_name = post_request_key[len(DRIVER_PREFIX):]
                    need_config_save |= self._update_logger_level(logger_name, log_level_or_parent, AVAILABLE_LOG_LEVELS_WITH_PARENT, 'drivers')
                else:
                    _logger.warning('Unhandled iot logger: %s', post_request_key)

            # Update and save the config file (in case of IoT box reset)
            if need_config_save:
                with helpers.writable():
                    tools.config.save()
        drivers_list = helpers.list_file_by_os(get_resource_path('hw_drivers', 'iot_handlers', 'drivers'))
        interfaces_list = helpers.list_file_by_os(get_resource_path('hw_drivers', 'iot_handlers', 'interfaces'))
        return handler_list_template.render({
            'title': "Odoo's IoT Box - Handlers list",
            'breadcrumb': 'Handlers list',
            'drivers_list': drivers_list,
            'interfaces_list': interfaces_list,
            'server': helpers.get_odoo_server_url(),
            'root_logger_log_level': self._get_logger_effective_level_str(logging.getLogger()),
            'odoo_current_log_level': self._get_logger_effective_level_str(logging.getLogger('odoo')),
            'recommended_log_level': 'warning',
            'available_log_levels': AVAILABLE_LOG_LEVELS,
            'drivers_logger_info': self._get_iot_handlers_logger(drivers_list, 'drivers'),
            'interfaces_logger_info': self._get_iot_handlers_logger(interfaces_list, 'interfaces'),
        })

    @http.route('/load_iot_handlers', type='http', auth='none', website=True)
    def load_iot_handlers(self):
        helpers.download_iot_handlers(False)
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069/list_handlers'>"

    @http.route('/list_credential', type='http', auth='none', website=True)
    def list_credential(self):
        return list_credential_template.render({
            'title': "Odoo's IoT Box - List credential",
            'breadcrumb': 'List credential',
            'db_uuid': helpers.read_file_first_line('odoo-db-uuid.conf'),
            'enterprise_code': helpers.read_file_first_line('odoo-enterprise-code.conf'),
        })

    @http.route('/save_credential', type='http', auth='none', cors='*', csrf=False)
    def save_credential(self, db_uuid, enterprise_code):
        helpers.write_file('odoo-db-uuid.conf', db_uuid)
        helpers.write_file('odoo-enterprise-code.conf', enterprise_code)
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/clear_credential', type='http', auth='none', cors='*', csrf=False)
    def clear_credential(self):
        helpers.unlink_file('odoo-db-uuid.conf')
        helpers.unlink_file('odoo-enterprise-code.conf')
        helpers.odoo_restart(0)
        return "<meta http-equiv='refresh' content='20; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/wifi', type='http', auth='none', website=True)
    def wifi(self):
        return wifi_config_template.render({
            'title': 'Wifi configuration',
            'breadcrumb': 'Configure Wifi',
            'loading_message': 'Connecting to Wifi',
            'ssid': helpers.get_wifi_essid(),
        })

    @http.route('/wifi_connect', type='http', auth='none', cors='*', csrf=False)
    def connect_to_wifi(self, essid, password, persistent=False):
        if persistent:
                persistent = "1"
        else:
                persistent = ""

        subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/connect_to_wifi.sh'), essid, password, persistent])
        server = helpers.get_odoo_server_url()
        res_payload = {
            'message': 'Connecting to ' + essid,
        }
        if server:
            res_payload['server'] = {
                'url': server,
                'message': 'Redirect to Odoo Server'
            }
        else:
            res_payload['server'] = {
                'url': 'http://' + helpers.get_ip() + ':8069',
                'message': 'Redirect to IoT Box'
            }

        return json.dumps(res_payload)

    @http.route('/wifi_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_wifi_configuration(self):
        helpers.unlink_file('wifi_network.txt')
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/server_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_server_configuration(self):
        helpers.unlink_file('odoo-remote-server.conf')
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/handlers_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_handlers_list(self):
        for directory in ['drivers', 'interfaces']:
            for file in list(Path(get_resource_path('hw_drivers', 'iot_handlers', directory)).glob('*')):
                if file.name != '__pycache__':
                    helpers.unlink_file(str(file.relative_to(*file.parts[:3])))
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069/list_handlers'>"

    @http.route('/server_connect', type='http', auth='none', cors='*', csrf=False)
    def connect_to_server(self, token, iotname):
        if token:
            credential = token.split('|')
            url = credential[0]
            token = credential[1]
            db_uuid = credential[2]
            enterprise_code = credential[3]
            helpers.save_conf_server(url, token, db_uuid, enterprise_code)
        else:
            url = helpers.get_odoo_server_url()
            token = helpers.get_token()
        if iotname and platform.system() == 'Linux':
            subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/rename_iot.sh'), iotname])
        helpers.odoo_restart(5)
        return 'http://' + helpers.get_ip() + ':8069'

    @http.route('/steps', type='http', auth='none', cors='*', csrf=False)
    def step_by_step_configure_page(self):
        return configure_wizard_template.render({
            'title': 'Configure IoT Box',
            'breadcrumb': 'Configure IoT Box',
            'loading_message': 'Configuring your IoT Box',
            'ssid': helpers.get_wifi_essid(),
            'server': helpers.get_odoo_server_url() or '',
            'hostname': subprocess.check_output('hostname').decode('utf-8').strip('\n'),
        })

    @http.route('/step_configure', type='http', auth='none', cors='*', csrf=False)
    def step_by_step_configure(self, token, iotname, essid, password, persistent=False):
        if token:
            url = token.split('|')[0]
            token = token.split('|')[1]
        else:
            url = ''
        subprocess.check_call([get_resource_path('point_of_sale', 'tools/posbox/configuration/connect_to_server_wifi.sh'), url, iotname, token, essid, password, persistent])
        return url

    # Set server address
    @http.route('/server', type='http', auth='none', website=True)
    def server(self):
        return server_config_template.render({
            'title': 'IoT -> Odoo server configuration',
            'breadcrumb': 'Configure Odoo Server',
            'hostname': subprocess.check_output('hostname').decode('utf-8').strip('\n'),
            'server_status': helpers.get_odoo_server_url() or 'Not configured yet',
            'loading_message': 'Configure Domain Server'
        })

    # Get password
    @http.route('/hw_posbox_homepage/password', type='json', auth='none', methods=['POST'])
    def view_password(self):
        return helpers.generate_password()

    @http.route('/remote_connect', type='http', auth='none', cors='*')
    def remote_connect(self):
        """
        Establish a link with a customer box trough internet with a ssh tunnel
        1 - take a new auth_token on https://dashboard.ngrok.com/
        2 - copy past this auth_token on the IoT Box : http://IoT_Box:8069/remote_connect
        3 - check on ngrok the port and url to get access to the box
        4 - you can connect to the box with this command : ssh -p port -v pi@url
        """
        return remote_connect_template.render({
            'title': 'Remote debugging',
            'breadcrumb': 'Remote Debugging',
        })

    @http.route('/enable_ngrok', type='http', auth='none', cors='*', csrf=False)
    def enable_ngrok(self, auth_token):
        if subprocess.call(['pgrep', 'ngrok']) == 1:
            subprocess.Popen(['ngrok', 'tcp', '-authtoken', auth_token, '-log', '/tmp/ngrok.log', '22'])
            return 'starting with ' + auth_token
        else:
            return 'already running'

    @http.route('/six_payment_terminal', type='http', auth='none', cors='*', csrf=False)
    def six_payment_terminal(self):
        return six_payment_terminal_template.render({
            'title': 'Six Payment Terminal',
            'breadcrumb': 'Six Payment Terminal',
            'terminalId': self.get_six_terminal(),
        })

    @http.route('/six_payment_terminal_add', type='http', auth='none', cors='*', csrf=False)
    def add_six_payment_terminal(self, terminal_id):
        if terminal_id.isdigit():
            helpers.write_file('odoo-six-payment-terminal.conf', terminal_id)
            service.server.restart()
        else:
            _logger.warning('Ignoring invalid Six TID: "%s". Only digits are allowed', terminal_id)
            self.clear_six_payment_terminal()
        return 'http://' + helpers.get_ip() + ':8069'

    @http.route('/six_payment_terminal_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_six_payment_terminal(self):
        helpers.unlink_file('odoo-six-payment-terminal.conf')
        service.server.restart()
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069'>"

    @http.route('/hw_proxy/upgrade', type='http', auth='none', )
    def upgrade(self):
        commit = subprocess.check_output(["git", "--work-tree=/home/pi/odoo/", "--git-dir=/home/pi/odoo/.git", "log", "-1"]).decode('utf-8').replace("\n", "<br/>")
        flashToVersion = helpers.check_image()
        actualVersion = helpers.get_version()
        if flashToVersion:
            flashToVersion = '%s.%s' % (flashToVersion.get('major', ''), flashToVersion.get('minor', ''))
        return upgrade_page_template.render({
            'title': "Odoo's IoTBox - Software Upgrade",
            'breadcrumb': 'IoT Box Software Upgrade',
            'loading_message': 'Updating IoT box',
            'commit': commit,
            'flashToVersion': flashToVersion,
            'actualVersion': actualVersion,
        })

    @http.route('/hw_proxy/perform_upgrade', type='http', auth='none')
    def perform_upgrade(self):
        self.updating.acquire()
        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/posbox_update.sh')
        self.updating.release()
        return 'SUCCESS'

    @http.route('/hw_proxy/get_version', type='http', auth='none')
    def check_version(self):
        return helpers.get_version()

    @http.route('/hw_proxy/perform_flashing_create_partition', type='http', auth='none')
    def perform_flashing_create_partition(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; create_partition']).decode().split('\n')[-2]
            if response in ['Error_Card_Size', 'Error_Upgrade_Already_Started']:
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            _logger.error('A error encountered : %s ' % e)
            return Response(str(e), status=500)

    @http.route('/hw_proxy/perform_flashing_download_raspios', type='http', auth='none')
    def perform_flashing_download_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; download_raspios']).decode().split('\n')[-2]
            if response == 'Error_Raspios_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.error('A error encountered : %s ' % e)
            return Response(str(e), status=500)

    @http.route('/hw_proxy/perform_flashing_copy_raspios', type='http', auth='none')
    def perform_flashing_copy_raspios(self):
        try:
            response = subprocess.check_output(['sudo', 'bash', '-c', '. /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/upgrade.sh; copy_raspios']).decode().split('\n')[-2]
            if response == 'Error_Iotbox_Download':
                raise Exception(response)
            return Response('success', status=200)
        except subprocess.CalledProcessError as e:
            raise Exception(e.output)
        except Exception as e:
            self.clean_partition()
            _logger.error('A error encountered : %s ' % e)
            return Response(str(e), status=500)

    @http.route('/iot_restart_odoo_or_reboot', type='json', auth='none', cors='*', csrf=False)
    def iot_restart_odoo_or_reboot(self, action):
        """ Reboots the IoT Box / restarts Odoo on it depending on chosen 'action' argument"""
        try:
            if action == 'restart_odoo':
                helpers.odoo_restart(3)
            else:
                subprocess.call(['sudo', 'reboot'])
            return 'success'
        except Exception as e:
            _logger.error('An error encountered : %s ', e)
            return str(e)

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
        return odoo_addon_handler_path in logging.Logger.manager.loggerDict.keys() and \
               logging.getLogger(odoo_addon_handler_path)

    def _update_logger_level(self, logger_name, new_level, available_log_levels, handler_folder=False):
        """
        Update (if necessary) Odoo's configuration and logger to the given logger_name to the given level.
        The responsibility of saving the config file is not managed here.
        :param logger_name: name of the logging logger to change level
        :param new_level: new log level to set for this logger
        :param available_log_levels: iterable of logs levels allowed (for initial check)
        :param handler_folder: optional string of the IoT handler folder name ('interfaces' or 'drivers')
        :return: wherever some changes were performed or not on the config
        """
        if new_level not in available_log_levels:
            _logger.warning('Unknown level to set on logger %s: %s', logger_name, new_level)
            return False

        if handler_folder:
            logger = self._get_iot_handler_logger(logger_name, handler_folder)
            if not logger:
                _logger.warning('Unable to change log level for logger %s as logger missing', logger_name)
                return False
            logger_name = logger.name

        ODOO_TOOL_CONFIG_HANDLER_NAME = 'log_handler'
        LOG_HANDLERS = tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME]
        LOGGER_PREFIX = logger_name + ':'
        IS_NEW_LEVEL_PARENT = new_level == 'parent'

        if not IS_NEW_LEVEL_PARENT:
            intended_to_find = LOGGER_PREFIX + new_level.upper()
            if intended_to_find in LOG_HANDLERS:
                # There is nothing to do, the entry is already inside
                return False

        # We remove every occurrence for the given logger
        log_handlers_without_logger = [
            log_handler for log_handler in LOG_HANDLERS if not log_handler.startswith(LOGGER_PREFIX)
        ]

        if IS_NEW_LEVEL_PARENT:
            # We must check that there is no existing entries using this logger (whatever the level)
            if len(log_handlers_without_logger) == len(LOG_HANDLERS):
                return False

        # We add if necessary new logger entry
        # If it is "parent" it means we want it to inherit from the parent logger.
        # In order to do this we have to make sure that no entries for the logger exists in the
        # `log_handler` (which is the case at this point as long as we don't re-add an entry)
        tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME] = log_handlers_without_logger
        new_level_upper_case = new_level.upper()
        if not IS_NEW_LEVEL_PARENT:
            new_entry = [LOGGER_PREFIX + new_level_upper_case]
            tools.config[ODOO_TOOL_CONFIG_HANDLER_NAME] += new_entry
            _logger.debug('Adding to odoo config log_handler: %s', new_entry)

        # Update the logger dynamically
        real_new_level = logging.NOTSET if IS_NEW_LEVEL_PARENT else new_level_upper_case
        _logger.debug('Change logger %s level to %s', logger_name, real_new_level)
        logging.getLogger(logger_name).setLevel(real_new_level)
        return True

    def _get_iot_handlers_logger(self, handlers_name, iot_handler_folder_name):
        """
        :param handlers_name: List of IoT handler string to search the loggers of
        :param iot_handler_folder_name: name of the handler folder ('interfaces' or 'drivers')
        :return:
        {
            <iot_handler_name_1> : {
                'level': <logger_level_1>,
                'is_using_parent_level': <logger_use_parent_level_or_not_1>,
                'parent_name': <logger_parent_name_1>,
            },
            ...
        }
        """
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
