# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import os
import requests
import subprocess
import time
import werkzeug

from odoo import http
from odoo.addons.hw_drivers.browser import Browser, BrowserState
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers, wifi
from odoo.addons.hw_drivers.tools.helpers import Orientation
from odoo.tools.misc import file_path


class DisplayDriver(Driver):
    connection_type = 'display'

    def __init__(self, identifier, device):
        super(DisplayDriver, self).__init__(identifier, device)
        self.device_type = 'display'
        self.device_connection = 'hdmi'
        self.device_name = device['name']
        self.owner = False
        self.customer_display_data = {}
        self.url, self.orientation = helpers.load_browser_state()
        if self.device_identifier != 'distant_display':
            self._x_screen = device.get('x_screen', '0')
            self.browser = Browser(
                self.url or 'http://localhost:8069/status/',
                self._x_screen,
                os.environ.copy(),
            )
            self.update_url(self.get_url_from_db())

        self._actions.update({
            'update_url': self._action_update_url,
            'display_refresh': self._action_display_refresh,
        })

        self.set_orientation(self.orientation)

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
            if self.url != 'http://localhost:8069/status/' and self.browser.state != BrowserState.KIOSK:
                # Refresh the page every minute
                self.browser.refresh()

    def update_url(self, url=None):
        self.url = (
            url
            or helpers.load_browser_state()[0]
            or 'http://localhost:8069/status/'
        )

        browser_state = BrowserState.KIOSK if "/pos-self/" in self.url else BrowserState.FULLSCREEN
        self.browser.open_browser(self.url, browser_state)

    @helpers.require_db
    def get_url_from_db(self):
        server_url = helpers.get_odoo_server_url()
        try:
            response = requests.get(f"{server_url}/iot/box/{helpers.get_mac_address()}/display_url", timeout=5)
            response.raise_for_status()
            data = json.loads(response.content.decode())
            return data.get(self.device_identifier)
        except requests.exceptions.RequestException:
            _logger.exception("Failed to get display URL from server")
        except json.decoder.JSONDecodeError:
            return response.content.decode('utf8')

    def _action_update_url(self, data):
        if self.device_identifier != 'distant_display':
            self.update_url(data.get('url'))

    def _action_display_refresh(self, data):
        if self.device_identifier != 'distant_display':
            self.browser.refresh()

    def set_orientation(self, orientation=Orientation.NORMAL):
        if self.device_identifier == 'distant_display':
            # Avoid calling xrandr if no display is connected
            return

        if type(orientation) is not Orientation:
            raise TypeError("orientation must be of type Orientation")
        subprocess.run(['xrandr', '-o', orientation.value], check=True)
        subprocess.run([file_path('hw_drivers/tools/sync_touchscreen.sh'), str(int(self._x_screen) + 1)], check=False)
        helpers.save_browser_state(orientation=orientation)


class DisplayController(http.Controller):
    @http.route('/hw_proxy/customer_facing_display', type='jsonrpc', auth='none', cors='*')
    def customer_facing_display(self, action, pos_id=None, access_token=None, data=None):
        display = self.ensure_display()
        if action in ['open', 'open_kiosk']:
            origin = helpers.get_odoo_server_url()
            if action == 'open_kiosk':
                url = f"{origin}/pos-self/{pos_id}?access_token={access_token}"
                display.set_orientation(Orientation.RIGHT)
            else:
                url = f"{origin}/pos_customer_display/{pos_id}/{access_token}"
            display.update_url(url)
            return {'status': 'opened'}
        if action == 'close':
            helpers.unlink_file('browser-url.conf')
            helpers.unlink_file('screen-orientation.conf')
            display.browser.disable_kiosk_mode()
            display.update_url()
            return {'status': 'closed'}
        if action == 'set':
            display.customer_display_data = data
            return {'status': 'updated'}
        if action == 'get':
            return {'status': 'retrieved', 'data': display.customer_display_data}
        if action == 'rotate_screen':
            display.set_orientation(Orientation(data))
            return {'status': 'rotated'}

    def ensure_display(self):
        display: DisplayDriver = DisplayDriver.get_default_display()
        if not display:
            raise werkzeug.exceptions.ServiceUnavailable(description="No display connected")
        return display
