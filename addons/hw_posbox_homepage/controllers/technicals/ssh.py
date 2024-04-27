
import subprocess

from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_posbox_homepage.controllers.technical import IoTTechnicalPage, get_menu


class IoTBoxTechnicalSSHPage(http.Controller, IoTTechnicalPage):
    _menu = get_menu(__name__)

    @http.route(_menu.url, type='http', auth='none')
    def ssh(self):
        return self.render(ip=helpers.get_ip())

    @http.route('/enable_ngrok', type='http', auth='none', cors='*', csrf=False)
    def enable_ngrok(self, auth_token):
        if subprocess.call(['pgrep', 'ngrok']) == 1:
            subprocess.Popen(['ngrok', 'tcp', '--authtoken', auth_token, '--log', '/tmp/ngrok.log', '22'])
            return 'starting with ' + auth_token
        else:
            return 'already running'

    @http.route('/hw_posbox_homepage/password', type='json', auth='none', methods=['POST'])
    def view_password(self):
        return helpers.generate_password()
