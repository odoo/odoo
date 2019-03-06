# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.tools import config
from odoo.addons.web.controllers import main as web
from openerp.addons.hw_posbox_homepage.controllers import main as homepage

import jinja2
import json
import logging
import netifaces as ni
import os
from subprocess import call
import sys
import time
import threading

self_port = str(config['http_port'] or 8069)

_logger = logging.getLogger(__name__)

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.hw_screen', "views")

jinja_env = jinja2.Environment(loader=loader, autoescape=True)
jinja_env.filters["json"] = json.dumps

pos_display_template = jinja_env.get_template('pos_display.html')


class Homepage(homepage.IoTboxHomepage):

    def get_hw_screen_message(self):
        return """
<p>
If you need to display the current customer basket on another device, you can do it <a href='/point_of_sale/display'>here</a>.
</p>
"""

class HardwareScreen(web.Home):

    event_data = threading.Event()
    pos_client_data = {'rendered_html': False,
                       'ip_from': False}
    display_in_use = ''
    failure_count = {}

    def _call_xdotools(self, keystroke):
        os.environ['DISPLAY'] = ":0.0"
        os.environ['XAUTHORITY'] = "/run/lightdm/pi/xauthority"
        try:
            call(['xdotool', 'key', keystroke])
            return "xdotool succeeded in stroking " + keystroke
        except:
            return "xdotool threw an error, maybe it is not installed on the IoTBox"

    @http.route('/hw_proxy/display_refresh', type='json', auth='none', cors='*')
    def display_refresh(self):
        return self._call_xdotools('F5')

    # POS CASHIER'S ROUTES
    @http.route('/hw_proxy/customer_facing_display', type='json', auth='none', cors='*')
    def update_user_facing_display(self, html=None):
        request_ip = http.request.httprequest.remote_addr
        if request_ip == HardwareScreen.pos_client_data.get('ip_from', ''):
            HardwareScreen.pos_client_data['rendered_html'] = html
            HardwareScreen.event_data.set()

            return {'status': 'updated'}
        else:
            return {'status': 'failed'}

    @http.route('/hw_proxy/take_control', type='json', auth='none', cors='*')
    def take_control(self, html=None):
        # ALLOW A CASHIER TO TAKE CONTROL OVER THE POSBOX, IN CASE OF MULTIPLE CASHIER PER POSBOX
        HardwareScreen.pos_client_data['rendered_html'] = html
        HardwareScreen.pos_client_data['ip_from'] = http.request.httprequest.remote_addr
        HardwareScreen.event_data.set()

        return {'status': 'success',
                'message': 'You now have access to the display'}

    @http.route('/hw_proxy/test_ownership', type='json', auth='none', cors='*')
    def test_ownership(self):
        if HardwareScreen.pos_client_data.get('ip_from') == http.request.httprequest.remote_addr:
            return {'status': 'OWNER'}
        else:
            return {'status': 'NOWNER'}

    # POSBOX ROUTES (SELF)
    @http.route('/point_of_sale/display', type='http', auth='none')
    def render_main_display(self):
        return self._get_html()

    @http.route('/point_of_sale/get_serialized_order', type='json', auth='none')
    def get_serialized_order(self):
        request_addr = http.request.httprequest.remote_addr
        result = HardwareScreen.pos_client_data
        if HardwareScreen.display_in_use and request_addr != HardwareScreen.display_in_use:
            if not HardwareScreen.failure_count.get(request_addr):
                HardwareScreen.failure_count[request_addr] = 0
            if HardwareScreen.failure_count[request_addr] > 0:
                time.sleep(10)
            HardwareScreen.failure_count[request_addr] += 1
            return {
                'rendered_html': False,
                'error': "Not Authorized. Another browser is in use to display for the client. Please refresh.",
                'stop_longpolling': True,
                'ip_from': request_addr,
            }

        # IMPLEMENTATION OF LONGPOLLING
        # Times out 2 seconds before the JS request does
        if HardwareScreen.event_data.wait(28):
            HardwareScreen.event_data.clear()
            HardwareScreen.failure_count[request_addr] = 0
            return result
        return {
            'rendered_html': False,
            'ip_from': HardwareScreen.pos_client_data['ip_from'],
        }

    def _get_html(self):
        cust_js = None
        interfaces = ni.interfaces()
        HardwareScreen.display_in_use = http.request.httprequest.remote_addr

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

        return pos_display_template.render({
            'title': "Odoo -- Point of Sale",
            'breadcrumb': 'POS Client display',
            'cust_js': cust_js,
            'display_ifaces': display_ifaces,
        })
