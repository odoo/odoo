# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import sub, finditer
import subprocess

from odoo.addons.hw_drivers.interface import Interface


class DisplayInterface(Interface):
    _loop_delay = 0
    connection_type = 'display'

    def get_devices(self):
        display_devices = {}
        displays = subprocess.check_output(['tvservice', '-l']).decode()
        x_screen = 0
        for match in finditer('Display Number (\d), type HDMI (\d)', displays):
            display_id, hdmi_id = match.groups()
            tvservice_output = subprocess.check_output(['tvservice', '-nv', display_id]).decode().strip()
            if tvservice_output:
                display_name = tvservice_output.split('=')[1]
                display_identifier = sub('[^a-zA-Z0-9 ]+', '', display_name).replace(' ', '_') + "_" + str(hdmi_id)
                iot_device = {
                    'identifier': display_identifier,
                    'name': display_name,
                    'x_screen': str(x_screen),
                }
                display_devices[display_identifier] = iot_device
                x_screen += 1

        if not len(display_devices):
            # No display connected, create "fake" device to be accessed from another computer
            display_devices['distant_display'] = {
                'name': "Distant Display",
            }

        return display_devices
