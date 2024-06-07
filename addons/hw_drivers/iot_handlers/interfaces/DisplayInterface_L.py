# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
try:
    import screeninfo
except ImportError:
    screeninfo = None

from odoo.addons.hw_drivers.interface import Interface

_logger = logging.getLogger(__name__)


class DisplayInterface(Interface):
    _loop_delay = 0
    connection_type = 'display'

    def get_devices(self):
        display_devices = {}

        if screeninfo is None:
            # On IoT image < 24.08 we don't have screeninfo installed, so we can't get the connected displays
            # We return a single display with x_screen = 0, to open a browser anyway, in case one is connected
            display_identifier = 'hdmi_0'
            display_devices[display_identifier] = {
                'identifier': display_identifier,
                'name': 'Display - ' + display_identifier,
                'x_screen': '0',
            }
            return display_devices

        try:
            os.environ['DISPLAY'] = ':0'
            for x_screen, monitor in enumerate(screeninfo.get_monitors()):
                display_identifier = monitor.name
                display_devices[display_identifier] = {
                    'identifier': display_identifier,
                    'name': 'Display - ' + display_identifier,
                    'x_screen': str(x_screen),
                }
        except screeninfo.common.ScreenInfoError:
            # If no display is connected, screeninfo raises an error, we return the distant display
            display_devices['distant_display'] = {
                'name': "Distant Display",
            }

        return display_devices
