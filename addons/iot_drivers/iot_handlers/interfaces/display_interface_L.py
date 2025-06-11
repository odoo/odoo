# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
import screeninfo
import subprocess

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools import helpers

_logger = logging.getLogger(__name__)

MIN_IMAGE_VERSION_WAYLAND = 25.03


class DisplayInterface(Interface):
    _loop_delay = 3
    connection_type = 'display'

    def get_devices(self):
        dummy_display = {
            'distant_display': {
                'identifier': 'distant_display',
                'name': 'Distant Display',
            }
        }

        if float(helpers.get_version()[1:]) >= MIN_IMAGE_VERSION_WAYLAND:
            randr_result = subprocess.run(['wlr-randr'], capture_output=True, text=True, check=False)
            if randr_result.returncode != 0:
                return {}
            displays = re.findall(r"\((HDMI-A-\d)\)", randr_result.stdout)
            return {
                monitor: self._add_device(monitor, x_screen)
                for x_screen, monitor in enumerate(displays)
            }

        try:
            os.environ['DISPLAY'] = ':0'
            display_devices = {
                monitor.name: self._add_device(monitor.name, x_screen)
                for x_screen, monitor in enumerate(screeninfo.get_monitors())
                if "DUMMY" not in monitor.name
            }
            return display_devices or dummy_display
        except screeninfo.common.ScreenInfoError:
            # If no display is connected, screeninfo raises an error, we return the distant display
            return dummy_display

    @classmethod
    def _add_device(cls, display_identifier, x_screen):
        """Creates a display_device dict.

        :param display_identifier: the identifier of the display
        :param x_screen: the x screen number
        :return: the display device dict
        """

        return {
            'identifier': display_identifier,
            'name': 'Display - ' + display_identifier,
            'x_screen': str(x_screen),
        }
