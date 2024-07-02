# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import subprocess
import os

from odoo.addons.hw_drivers.interface import Interface

_logger = logging.getLogger(__name__)


class DisplayInterface(Interface):
    _loop_delay = 0
    connection_type = 'display'

    def get_devices(self):
        display_devices = {}

        try:
            # Get xrandr output and parse lines
            # 'check_output' method returns a bytes object, so we need to decode it to a string and split it by lines
            # 'split' method is used to get only the last element of each line : 'number of monitors' then 'identifiers'
            # check if 'xrandr:' in o to get rid of information message if xrandr badly configured
            os.environ['DISPLAY'] = ":0"
            monitors_names = [
                o.split()[-1]
                for o in subprocess.check_output(['xrandr', '--listactivemonitors'], stderr=subprocess.DEVNULL)
                .decode('utf-8')
                .split('\n')
                if o
            ]
            # Skip the first line which is the number of monitors
            hdmi_monitors = [
                name for name in monitors_names[1:]
                if any(substr in name for substr in ['HDMI', 'Composite', 'default'])  # default for images < v26.04
            ]

            for x_screen, name in enumerate(hdmi_monitors):
                hdmi = 'hdmi_' + str(x_screen)
                display_devices[hdmi] = {
                    'identifier': hdmi,
                    'name': 'Display - ' + name,
                    'x_screen': str(x_screen),
                }
        except subprocess.CalledProcessError as se:
            _logger.warning('xrandr command failed with error: %s', se.stderr.decode('utf-8'))

        if not len(display_devices):
            # No display connected, create "fake" device to be accessed from another computer
            display_devices['distant_display'] = {
                'name': "Distant Display",
            }

        return display_devices
