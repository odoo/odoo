# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
import subprocess

from odoo.addons.iot_drivers.interface import Interface

_logger = logging.getLogger(__name__)


class DisplayInterface(Interface):
    _loop_delay = 3
    connection_type = 'display'

    def get_devices(self):
        randr_result = subprocess.run(['wlr-randr'], capture_output=True, text=True, check=False)
        if randr_result.returncode != 0:
            return {}
        displays = re.findall(r"\((HDMI-A-\d)\)", randr_result.stdout)
        return {
            monitor: self._add_device(monitor, x_screen)
            for x_screen, monitor in enumerate(displays)
        }

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
