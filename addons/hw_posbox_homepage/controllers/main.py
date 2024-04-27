# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import platform
import logging
from pathlib import Path
import socket
import subprocess

from odoo import http
from odoo.modules.module import get_resource_path
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.server_logger import close_server_log_sender_handler
from odoo.addons.hw_posbox_homepage.controllers.jinja import jinja_env
from odoo.addons.hw_posbox_homepage.controllers.table_info import TableInfo
from odoo.addons.web.controllers.home import Home

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

homepage_template = jinja_env.get_template('homepage.jinja2')
homepage_table_devices = jinja_env.get_template('_homepage_table_devices.jinja2')
server_config_template = jinja_env.get_template('server_config.jinja2')
configure_wizard_template = jinja_env.get_template('configure_wizard.jinja2')

class IoTboxHomepage(Home):
    def get_homepage_data(self):
        system = platform.system()

        hostname = socket.gethostname()
        odoo_server = helpers.get_odoo_server_url()

        homepage_table = [
            TableInfo('Name', hostname, system == 'Linux' and '/server', name_icon='id-card-o'),
            TableInfo(
                'Odoo Server',
                f"<a href='{odoo_server}' target='_blank'>{odoo_server}</a>" if odoo_server else '<i>Not Configured<i>',
                '/server',
                iot_documentation_url='/config/connect.html',
                name_icon='globe',
                is_warning=not odoo_server),
        ]

        pairing_code = connection_manager.pairing_code
        if pairing_code:
            homepage_table.append(TableInfo(
                'Pairing Code',
                pairing_code,
                iot_documentation_url='/config/connect.html#ethernet-connection',
                name_icon='link'
                )
            )

        iot_devices_render = []
        for device in iot_devices.values():
            iot_devices_render.append({
                'name': device.device_name + ' : ' + str(device.data['value']),
                'type': device.device_type.replace('_', ' '),
                'identifier': device.device_identifier,
            })
        homepage_table.append(TableInfo(
            'Devices',
            homepage_table_devices.render(iot_devices=iot_devices_render),
            iot_documentation_url='/devices.html',
            name_icon='plug'
            )
        )

        return {
            'homepage_table': homepage_table,
        }

    @http.route('/', type='http', auth='none')
    def index(self):
        # TODO: this checks are useless on windows and 99% useless on iot-box
        #    use a smarter system to gain on performances
        wifi = Path.home() / 'wifi_network.txt'
        remote_server = Path.home() / 'odoo-remote-server.conf'
        if (wifi.exists() == False or remote_server.exists() == False) and helpers.access_point():
            return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069/steps'>"
        else:
            return homepage_template.render(self.get_homepage_data())

    @http.route('/server_clear', type='http', auth='none', cors='*', csrf=False)
    def clear_server_configuration(self):
        helpers.unlink_file('odoo-remote-server.conf')
        close_server_log_sender_handler()
        return "<meta http-equiv='refresh' content='0; url=http://" + helpers.get_ip() + ":8069'>"

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
