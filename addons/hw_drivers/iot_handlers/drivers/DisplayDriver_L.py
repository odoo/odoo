# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import jinja2
import json
import logging
import netifaces as ni
import os
import subprocess
import socket
import threading
import time
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
        self.event_data = threading.Event()
        self.owner = False
        self.rendered_html = ''
        if self.device_identifier != 'distant_display':
            # helpers.get_version returns a string formatted as: <L|W><version> (L: Linux, W: Windows)
            self.browser = 'chromium-browser' if float(helpers.get_version()[1:]) >= 24.08 else 'firefox'
            self._x_screen = device.get('x_screen', '0')
            self.load_url()

        self._actions.update({
            'update_url': self._action_update_url,
            'display_refresh': self._action_display_refresh,
            'take_control': self._action_take_control,
            'customer_facing_display': self._action_customer_facing_display,
            'get_owner': self._action_get_owner,
        })

    @classmethod
    def supported(cls, device):
        return True  # All devices with connection_type == 'display' are supported

    @classmethod
    def get_default_display(cls):
        displays = list(filter(lambda d: iot_devices[d].device_type == 'display', iot_devices))
        return len(displays) and iot_devices[displays[0]]

    def run(self):
        while self.device_identifier != 'distant_display' and not self._stopped.is_set():
            time.sleep(60)
            if self.url != 'http://localhost:8069/point_of_sale/display/' + self.device_identifier:
                # Refresh the page every minute
                self.call_xdotools('F5')

    def update_url(self, url=None):
        os.environ['DISPLAY'] = ":0." + self._x_screen
        os.environ['XAUTHORITY'] = '/run/lightdm/pi/xauthority'
        browser_env = os.environ.copy()
        for key in ['HOME', 'XDG_RUNTIME_DIR', 'XDG_CACHE_HOME']:
            browser_env[key] = '/tmp/' + self._x_screen
        self.url = url or 'http://localhost:8069/point_of_sale/display/' + self.device_identifier

        # Kill browser instance (can't `instance.pkill()` as we can't keep the instance after Odoo service restarts)
        # We need to terminate it because Odoo will create a new instance each time it is restarted.
        subprocess.run(['pkill', self.browser.split('-')[0]], check=False)
        # --log-level=3 to avoid useless log messages, --bwsi to use chromium without signing in
        browser_args = ['--start-fullscreen', '--log-level=3', '--bwsi']
        subprocess.Popen([self.browser, self.url, *browser_args], env=browser_env)

        # To remove when everyone is on version >= 24.08: chromium has '--start-fullscreen' option
        if self.browser == 'firefox':
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
            subprocess.run([
                'xdotool',
                'search',
                '--sync',
                '--onlyvisible',
                '--screen',
                self._x_screen,
                '--class',
                self.browser,
                'key',
                keystroke,
            ], check=False)
            return "xdotool succeeded in stroking " + keystroke
        except:
            return "xdotool threw an error, maybe it is not installed on the IoTBox"

    def update_customer_facing_display(self, origin, html=None):
        if origin == self.owner:
            self.rendered_html = html
            self.event_data.set()

    def get_serialized_order(self):
        # IMPLEMENTATION OF LONGPOLLING
        # Times out 2 seconds before the JS request does
        if self.event_data.wait(28):
            self.event_data.clear()
            return {'rendered_html': self.rendered_html}
        return {'rendered_html': False}

    def take_control(self, new_owner, html=None):
        # ALLOW A CASHIER TO TAKE CONTROL OVER THE POSBOX, IN CASE OF MULTIPLE CASHIER PER DISPLAY
        self.owner = new_owner
        self.rendered_html = html
        self.data = {
            'value': '',
            'owner': self.owner,
        }
        event_manager.device_changed(self)
        self.event_data.set()

    def _action_update_url(self, data):
        if self.device_identifier != 'distant_display':
            self.update_url(data.get('url'))

    def _action_display_refresh(self, data):
        if self.device_identifier != 'distant_display':
            self.call_xdotools('F5')

    def _action_take_control(self, data):
        self.take_control(self.data.get('owner'), data.get('html'))

    def _action_customer_facing_display(self, data):
        self.update_customer_facing_display(self.data.get('owner'), data.get('html'))

    def _action_get_owner(self, data):
        self.data = {
            'value': '',
            'owner': self.owner,
        }
        event_manager.device_changed(self)


class DisplayController(http.Controller):
    @http.route('/hw_proxy/display_refresh', type='json', auth='none', cors='*')
    def display_refresh(self):
        display = DisplayDriver.get_default_display()
        if display and display.device_identifier != 'distant_display':
            return display.call_xdotools('F5')

    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def customer_facing_display(self, html=None):
        display = DisplayDriver.get_default_display()
        if display:
            display.update_customer_facing_display(http.request.httprequest.remote_addr, html)
            return {'status': 'updated'}
        return {'status': 'failed'}

    @http.route('/hw_proxy/take_control', type='json', auth='none', cors='*')
    def take_control(self, html=None):
        display = DisplayDriver.get_default_display()
        if display:
            display.take_control(http.request.httprequest.remote_addr, html)
            return {
                'status': 'success',
                'message': 'You now have access to the display',
            }

    @http.route('/hw_proxy/test_ownership', type='json', auth='none', cors='*')
    def test_ownership(self):
        display = DisplayDriver.get_default_display()
        if display and display.owner == http.request.httprequest.remote_addr:
            return {'status': 'OWNER'}
        return {'status': 'NOWNER'}

    @http.route(['/point_of_sale/get_serialized_order', '/point_of_sale/get_serialized_order/<string:display_identifier>'], type='json', auth='none')
    def get_serialized_order(self, display_identifier=None):
        if display_identifier:
            display = iot_devices.get(display_identifier)
        else:
            display = DisplayDriver.get_default_display()

        if display:
            return display.get_serialized_order()
        return {
            'rendered_html': False,
            'error': "No display found",
        }

    @http.route(['/point_of_sale/display', '/point_of_sale/display/<string:display_identifier>'], type='http', auth='none')
    def display(self, display_identifier=None):
        cust_js = None
        interfaces = ni.interfaces()

        with file_open("hw_drivers/static/src/js/worker.js") as js:
            cust_js = js.read()

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

        default_display = DisplayDriver.get_default_display()
        if not display_identifier and default_display != 0:
            display_identifier = default_display.device_identifier

        return pos_display_template.render({
            'title': "Odoo -- Point of Sale",
            'breadcrumb': 'POS Client display',
            'cust_js': cust_js,
            'display_ifaces': display_ifaces,
            'display_identifier': display_identifier,
            'hostname': socket.gethostname(),
            'pairing_code': connection_manager.pairing_code,
        })

    @http.route('/point_of_sale/iot_devices', type='json', auth='none', methods=['POST'])
    def get_iot_devices(self):
        iot_device = [{
            'name': iot_devices[device].device_name,
            'type': iot_devices[device].device_type,
        } for device in iot_devices]

        return json.dumps({'iot_device_status': iot_device})
