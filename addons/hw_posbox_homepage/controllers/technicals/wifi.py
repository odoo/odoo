
import json
import subprocess

from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.technical import IoTTechnicalPage, get_menu
from odoo.modules.module import get_resource_path


class IoTBoxTechnicalWifiPage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    @http.route(_menu.url, type='http', auth='none')
    def wifi(self):
        return self.render(
            loading_message='Connecting to Wifi',
            ssid=helpers.get_wifi_essid(),
        )

    @http.route('/wifi_connect', type='http', auth='none', cors='*', csrf=False)
    def connect_to_wifi(self, essid, password, persistent=False):
        persistent = "1" if persistent else ""

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
