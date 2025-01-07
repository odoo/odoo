# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import os
import requests
import subprocess
import time

from odoo.addons.hw_drivers.browser import Browser, BrowserState
from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.tools import helpers, wifi
from odoo.addons.hw_drivers.tools.helpers import Orientation
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.tools.misc import file_path

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
            'get_customer_display_data': self._action_get_customer_display_data,
            'set_customer_display_data': self._action_set_customer_display_data,
            'close_customer_display': self._action_close_customer_display,
            'open_customer_display': self._action_open_customer_display,
            'open_kiosk': self._action_open_kiosk,
            'rotate_screen': self._action_set_orientation,
        })

        self.set_orientation(self.orientation)

    @classmethod
    def supported(cls, device):
        return True  # All devices with connection_type == 'display' are supported

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

    def get_url_from_db(self):
        server_url = helpers.get_odoo_server_url()
        if server_url:
            try:
                response = requests.get(f"{server_url}/iot/box/{helpers.get_mac_address()}/display_url", timeout=5)
                response.raise_for_status()
                data = json.loads(response.content.decode())
                return data.get(self.device_identifier)
            except requests.exceptions.RequestException:
                _logger.exception("Failed to get display URL from server")
            except json.decoder.JSONDecodeError:
                return response.content.decode('utf8')

    def set_orientation(self, orientation=Orientation.NORMAL):
        if self.device_identifier == 'distant_display':
            # Avoid calling xrandr if no display is connected
            return

        if type(orientation) is not Orientation:
            raise TypeError("orientation must be of type Orientation")
        subprocess.run(['xrandr', '-o', orientation.value], check=True)
        subprocess.run([file_path('hw_drivers/tools/sync_touchscreen.sh'), str(int(self._x_screen) + 1)], check=False)
        helpers.save_browser_state(orientation=orientation)

    def _action_update_url(self, data):
        if self.device_identifier != 'distant_display':
            self.update_url(data.get('url'))
        event_manager.device_changed(self)

    def _action_display_refresh(self, _data):
        if self.device_identifier != 'distant_display':
            self.browser.refresh()
        event_manager.device_changed(self)

    def _action_get_customer_display_data(self, _data):
        """Return the data to be displayed on the customer facing display."""
        self.value = self.customer_display_data
        event_manager.device_changed(self)

    def _action_set_customer_display_data(self, data):
        """Set the data to be displayed on the customer facing display."""
        self.customer_display_data = data.get('data', {})
        event_manager.device_changed(self)

    def _action_open_customer_display(self, data):
        """Open the customer facing display."""
        if self.device_identifier == 'distant_display':
            return
        self.update_url(
            f"{helpers.get_odoo_server_url()}/pos_customer_display/{data['pos_id']}/{data['access_token']}"
        )
        event_manager.device_changed(self)

    def _action_close_customer_display(self, _data):
        """Close the customer facing display."""
        helpers.unlink_file('browser-url.conf')
        helpers.unlink_file('screen-orientation.conf')
        self.browser.disable_kiosk_mode()
        self.update_url()
        event_manager.device_changed(self)

    def _action_open_kiosk(self, data):
        """Switch to kiosk mode opening the PoS Self Order session."""
        if self.device_identifier == 'distant_display':
            return
        self.set_orientation(Orientation.RIGHT)
        self.update_url(
            f"{helpers.get_odoo_server_url()}/pos-self/{data['pos_id']}?access_token={data['access_token']}"
        )
        event_manager.device_changed(self)

    def _action_set_orientation(self, data):
        """Set the orientation of the screen."""
        self.set_orientation(Orientation(data.get('orientation', Orientation.NORMAL)))
        event_manager.device_changed(self)
