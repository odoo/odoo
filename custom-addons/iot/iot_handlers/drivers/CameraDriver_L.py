# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import subprocess

from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager


class CameraDriver(Driver):
    connection_type = 'video'

    def __init__(self, identifier, device):
        super(CameraDriver, self).__init__(identifier, device)
        self.device_type = 'camera'
        self.device_connection = 'direct'
        self.device_name = device.card.decode('utf-8')

        self._actions.update({
            '': self._action_default,
        })

    @classmethod
    def supported(cls, device):
        return device.driver.decode('utf-8') == 'uvcvideo'

    def _action_default(self, data):
        try:
            """
            Check the max resolution for webcam.
            Take picture, output it on stdout and convert it in base 64.
            Release Event with picture in data.
            """
            v4l2 = subprocess.Popen(['v4l2-ctl', '--list-formats-ext'], stdout=subprocess.PIPE)
            all_sizes = subprocess.Popen(['grep', 'Size'], stdin=v4l2.stdout, stdout=subprocess.PIPE)
            all_resolutions = subprocess.Popen(['awk', '{print $3}'], stdin=all_sizes.stdout, stdout=subprocess.PIPE)
            sorted_resolutions = subprocess.Popen(['sort', '-rn'], stdin=all_resolutions.stdout, stdout=subprocess.PIPE)
            resolution = subprocess.check_output(['awk', 'NR==1'], stdin=sorted_resolutions.stdout).decode('utf-8')
            self.data['image'] = base64.b64encode(subprocess.check_output(["fswebcam", "-d", self.dev.interface, "-", "-r", resolution]))
            self.data['message'] = 'Image captured'
        except subprocess.CalledProcessError as e:
            self.data['message'] = e.output
        event_manager.device_changed(self)
