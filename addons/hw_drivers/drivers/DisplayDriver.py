import jinja2
import json
import logging
import netifaces as ni
import os
from pathlib import Path
import subprocess
import threading
import time
import urllib3

from odoo import http
from odoo.addons.hw_drivers.tools import helpers
from odoo.addons.hw_drivers.controllers.driver import Driver, event_manager, iot_devices

path = os.path.realpath(os.path.join(os.path.dirname(__file__), '../views'))
loader = jinja2.FileSystemLoader(path)

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

pos_display_template = jinja_env.get_template('pos_display.html')

_logger = logging.getLogger(__name__)


class DisplayDriver(Driver):
    connection_type = 'display'

    def __init__(self, device):
        super(DisplayDriver, self).__init__(device)
        self._device_type = 'display'
        self._device_connection = 'hdmi'
        self._device_name = device['name']
        self.event_data = threading.Event()
        self.owner = False
        self.rendered_html = ''
        if self.device_identifier != 'distant_display':
            self._x_screen = device.get('x_screen', '0')
            self.load_url()

    @property
    def device_identifier(self):
        return self.dev['identifier']

    @classmethod
    def supported(cls, device):
        return True  # All devices with connection_type == 'display' are supported

    @classmethod
    def get_default_display(cls):
        displays = list(filter(lambda d: iot_devices[d].device_type == 'display', iot_devices))
        return len(displays) and iot_devices[displays[0]]

    def action(self, data):
        if data.get('action') == "update_url":
            self.update_url(data.get('url'))
        elif data.get('action') == "display_refresh":
            self.call_xdotools('F5')
        elif data.get('action') == "take_control":
            self.take_control(self.data['owner'], data.get('html'))
        elif data.get('action') == "customer_facing_display":
            self.update_customer_facing_display(self.data['owner'], data.get('html'))
        elif data.get('action') == "get_owner":
            self.data = {
                'value': '',
                'owner': self.owner,
            }
            event_manager.device_changed(self)

    def run(self):
        while self.device_identifier != 'distant_display':
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
                response = http.request('GET', "%s/iot/box/%s/screen_url" % (helpers.get_odoo_server_url(), helpers.get_mac_address()))
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

class DisplayController(http.Controller):

    @http.route('/hw_proxy/display_refresh', type='json', auth='none', cors='*')
    def display_refresh(self):
        display = DisplayDriver.get_default_display()
        if display:
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

        with open(os.path.join(os.path.dirname(__file__), "../static/src/js/worker.js")) as js:
            cust_js = js.read()

        display_ifaces = []
        for iface_id in interfaces:
            if 'wlan' in iface_id or 'eth' in iface_id:
                iface_obj = ni.ifaddresses(iface_id)
                ifconfigs = iface_obj.get(ni.AF_INET, [])
                for conf in ifconfigs:
                    if conf.get('addr'):
                        display_ifaces.append({
                            'iface_id': iface_id,
                            'addr': conf.get('addr'),
                            'icon': 'sitemap' if 'eth' in iface_id else 'wifi',
                        })

        if not display_identifier:
            display_identifier = DisplayDriver.get_default_display().device_identifier

        return pos_display_template.render({
            'title': "Odoo -- Point of Sale",
            'breadcrumb': 'POS Client display',
            'cust_js': cust_js,
            'display_ifaces': display_ifaces,
            'display_identifier': display_identifier,
        })
