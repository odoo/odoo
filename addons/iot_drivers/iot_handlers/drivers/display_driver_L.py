# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import os
import requests
import subprocess
import time
import werkzeug

from odoo import http
from odoo.addons.iot_drivers.browser import Browser, BrowserState
from odoo.addons.iot_drivers.driver import Driver
from odoo.addons.iot_drivers.main import iot_devices
from odoo.addons.iot_drivers.tools import helpers, route
from odoo.addons.iot_drivers.tools.helpers import Orientation
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)

MIN_IMAGE_VERSION_WAYLAND = 25.03


class DisplayDriver(Driver):
    connection_type = 'display'

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
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
            'open_kiosk': self._action_open_kiosk,
            'rotate_screen': self._action_rotate_screen,
            'open': self._action_open_customer_display,
            'close': self._action_close_customer_display,
            'set': self._action_set_customer_display,
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
    def get_url_from_db(self, server_url=None):
        """Get the display URL provided by the connected database.

        :param server_url: The URL of the connected database (provided by decorator).
        :return: URL to display or None.
        """
        try:
            response = requests.get(f"{server_url}/iot/box/{helpers.get_identifier()}/display_url", timeout=5)
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

    def _action_open_kiosk(self, data):
        if self.device_identifier != 'distant_display':
            origin = helpers.get_odoo_server_url()
            self.update_url(f"{origin}/pos-self/{data.get('pos_id')}?access_token={data.get('access_token')}")
            self.set_orientation(Orientation.RIGHT)

    def _action_rotate_screen(self, data):
        if self.device_identifier == 'distant_display':
            return

        orientation = data.get('orientation', 'NORMAL').upper()
        self.set_orientation(Orientation[orientation])

    def _action_open_customer_display(self, data):
        if self.device_identifier == 'distant_display' or not data.get('pos_id') or not data.get('access_token'):
            return

        origin = helpers.get_odoo_server_url() or http.request.httprequest.origin
        self.update_url(f"{origin}/pos_customer_display/{data['pos_id']}/{data['access_token']}")

    def _action_close_customer_display(self, data):
        if self.device_identifier == 'distant_display':
            return

        helpers.update_conf({"browser_url": "", "screen_orientation": ""})
        self.browser.disable_kiosk_mode()
        self.update_url()

    def _action_set_customer_display(self, data):
        if self.device_identifier == 'distant_display' or not data.get('data'):
            return

        self.data['customer_display_data'] = data['data']

    def set_orientation(self, orientation=Orientation.NORMAL):
        if self.device_identifier == 'distant_display':
            return

        if type(orientation) is not Orientation:
            raise TypeError("orientation must be of type Orientation")

        if float(helpers.get_version()[1:]) >= MIN_IMAGE_VERSION_WAYLAND:
            subprocess.run(['wlr-randr', '--output', self.device_identifier, '--transform', orientation.value], check=True)
            # Update touchscreen mapping to this display
            subprocess.run(
                ['sed', '-i', f's/HDMI-A-[12]/{self.device_identifier}/', '/home/odoo/.config/labwc/rc.xml'],
                check=False,
            )
            # Tell labwc to reload its configuration
            subprocess.run(['pkill', '-HUP', 'labwc'], check=False)
        else:
            subprocess.run(['xrandr', '-o', orientation.name.lower()], check=True)
            subprocess.run([file_path('iot_drivers/tools/sync_touchscreen.sh'), str(int(self._x_screen) + 1)], check=False)
        helpers.save_browser_state(orientation=orientation)


class DisplayController(http.Controller):
    @route.iot_route('/hw_proxy/customer_facing_display', type='jsonrpc', cors='*')
    def customer_facing_display(self):
        display = self.ensure_display()
        return display.data.get('customer_display_data', {})

    def ensure_display(self):
        display: DisplayDriver = DisplayDriver.get_default_display()
        if not display:
            raise werkzeug.exceptions.ServiceUnavailable(description="No display connected")
        return display
