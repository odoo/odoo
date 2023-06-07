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

from odoo import http, service
from odoo.http import Response
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

    @http.route('/list_handlers', type='http', auth='none', website=True)
    def list_handlers(self):
        drivers_list = helpers.list_file_by_os(get_resource_path('hw_drivers', 'iot_handlers', 'drivers'))
        interfaces_list = helpers.list_file_by_os(get_resource_path('hw_drivers', 'iot_handlers', 'interfaces'))
        return handler_list_template.render({
            'title': "Odoo's IoT Box - Handlers list",
            'breadcrumb': 'Handlers list',
            'drivers_list': drivers_list,
            'interfaces_list': interfaces_list,
            'server': helpers.get_odoo_server_url()
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
        else:
            helpers.odoo_restart(3)
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
        helpers.write_file('odoo-six-payment-terminal.conf', terminal_id)
        service.server.restart()
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
