# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import subprocess

from odoo.addons.iot_drivers.driver import Driver

_logger = logging.getLogger(__name__)


class CameraDriver(Driver):
    connection_type = 'video'

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_type = 'camera'
        self.device_connection = 'direct'
        self.device_name = device['name']
        self.interface = device['interface']

        self._actions.update({
            '': self._action_default,
        })

    @classmethod
    def supported(cls, device):
        return bool(device['interface'])

    def _action_default(self, _data):
        """Capture an image from the camera.
        The resolution is set to 1920x1080, but will be lowered if not supported.
        """
        # "-" to output to stdout (avoid writing to disk)
        image = subprocess.run(
            ["fswebcam", "-d", self.interface, "-r", "1920x1080", "-"], capture_output=True, check=False
        )
        if image.returncode == 0:
            return {
                'image': base64.b64encode(image.stdout).decode(),
            }
        else:
            _logger.error('Failed to capture image: %s', image.stderr.decode())
            raise Exception('Failed to capture image from camera.')
