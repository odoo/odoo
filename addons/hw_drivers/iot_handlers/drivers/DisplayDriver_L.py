# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import jinja2
import json
import logging
import netifaces as ni
import os
import subprocess
import threading
import time
import werkzeug

import urllib3

from odoo import http
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers
from odoo.tools.misc import file_open

path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../../views'))
loader = jinja2.FileSystemLoader(path)

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

pos_display_template = jinja_env.get_template('pos_display.html')

_logger = logging.getLogger(__name__)


class DisplayDriver(Driver):
    connection_type = 'display'

    def __init__(self, identifier, device):
        super(DisplayDriver, self).__init__(identifier, device)
        self.device_type = 'display'
        self.device_connection = 'hdmi'
        self.device_name = device['name']
        self.owner = False
        self.customer_display_data = {}
        if self.device_identifier != 'distant_display':
            self._x_screen = device.get('x_screen', '0')
            self.load_url()

        self._actions.update({
            'update_url': self._action_update_url,
            'display_refresh': self._action_display_refresh,
        })

    @classmethod
    def supported(cls, device):
        return True  # All devices with connection_type == 'display' are supported

    @classmethod
    def get_default_display(cls):
        displays = list(filter(lambda d: iot_devices[d].device_type == 'display', iot_devices))
        return len(displays) and iot_devices[displays[0]]

    def run(self):
        while self.device_identifier != 'distant_display' and not self._stopped.is_set() and "pos_customer_display" not in self.url:
            time.sleep(60)
            if self.url != 'http://localhost:8069/point_of_sale/display/' + self.device_identifier:
                # Refresh the page every minute
                self.call_xdotools('F5')

    def update_url(self, url=None):
        os.environ['DISPLAY'] = ":0." + self._x_screen
        os.environ['XAUTHORITY'] = '/run/lightdm/pi/xauthority'
        firefox_env = os.environ.copy()
        firefox_env['HOME'] = '/tmp/' + self._x_screen
        self.url = url or 'http://localhost:8069/point_of_sale/display/' + self.device_identifier
        new_window = subprocess.call(['xdotool', 'search', '--onlyvisible', '--screen', self._x_screen, '--class', 'Firefox'])
        subprocess.Popen(['firefox', self.url], env=firefox_env)
        if new_window:
            self.call_xdotools('F11')

    def load_url(self):
        url = None
        if helpers.get_odoo_server_url():
            # disable certifiacte verification
            urllib3.disable_warnings()
            http = urllib3.PoolManager(cert_reqs='CERT_NONE')
            try:
                response = http.request('GET', "%s/iot/box/%s/display_url" % (helpers.get_odoo_server_url(), helpers.get_mac_address()))
                if response.status == 200:
                    data = json.loads(response.data.decode('utf8'))
                    url = data[self.device_identifier]
            except json.decoder.JSONDecodeError:
                url = response.data.decode('utf8')
            except Exception:
                pass
        return self.update_url(url)

    def call_xdotools(self, keystroke):
        os.environ['DISPLAY'] = ":0." + self._x_screen
        os.environ['XAUTHORITY'] = "/run/lightdm/pi/xauthority"
        try:
            subprocess.call(['xdotool', 'search', '--sync', '--onlyvisible', '--screen', self._x_screen, '--class', 'Firefox', 'key', keystroke])
            return "xdotool succeeded in stroking " + keystroke
        except:
            return "xdotool threw an error, maybe it is not installed on the IoTBox"

    def _action_update_url(self, data):
        if self.device_identifier != 'distant_display':
            self.update_url(data.get('url'))

    def _action_display_refresh(self, data):
        if self.device_identifier != 'distant_display':
            self.call_xdotools('F5')

class DisplayController(http.Controller):
    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def customer_facing_display(self):
        data = http.request.get_json_data()
        if data['action'] == 'open':
            origin = helpers.get_odoo_server_url() or http.request.httprequest.referrer.split('://')[-1].split('/')[0]
            self.ensure_display().update_url(f"{origin}/pos_customer_display/{data['id']}/{data['access_token']}")
            return {'status': 'opened'}
        if data['action'] == 'close':
            self.ensure_display().update_url()
            return {'status': 'closed'}
        if data['action'] == 'set':
            self.ensure_display().customer_display_data = data['data']
            return {'status': 'updated'}
        if data['action'] == 'get':
            return {'status': 'retrieved', 'data': self.ensure_display().customer_display_data}

    def ensure_display(self):
        display = DisplayDriver.get_default_display()
        if not display:
            raise werkzeug.exceptions.ServiceUnavailable(description="No display connected")
        return display

    @http.route(['/point_of_sale/display', '/point_of_sale/display/<string:display_identifier>'], auth='none')
    def display(self, display_identifier=None):
        interfaces = ni.interfaces()

        display_ifaces = []
        for iface_id in interfaces:
            if 'wlan' in iface_id or 'eth' in iface_id:
                iface_obj = ni.ifaddresses(iface_id)
                ifconfigs = iface_obj.get(ni.AF_INET, [])
                essid = helpers.get_ssid()
                for conf in ifconfigs:
                    if conf.get('addr'):
                        display_ifaces.append({
                            'iface_id': iface_id,
                            'essid': essid,
                            'addr': conf.get('addr'),
                            'icon': 'sitemap' if 'eth' in iface_id else 'wifi',
                        })

        if not display_identifier:
            display_identifier = DisplayDriver.get_default_display().device_identifier

        return pos_display_template.render({
            'title': "Odoo -- Point of Sale",
            'breadcrumb': 'POS Client display',
            'display_ifaces': display_ifaces,
            'display_identifier': display_identifier,
            'pairing_code': connection_manager.pairing_code,
        })

    @http.route('/point_of_sale/iot_devices', type='json', auth='none', methods=['POST'])
    def get_iot_devices(self):
        iot_device = [{
            'name': iot_devices[device].device_name,
            'type': iot_devices[device].device_type,
        } for device in iot_devices]

        return json.dumps({'iot_device_status': iot_device})
