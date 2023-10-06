# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import sub, finditer
import subprocess
from vcgencmd import Vcgencmd
import RPi.GPIO as GPIO

from odoo.addons.hw_drivers.interface import Interface


class DisplayInterface(Interface):
    _loop_delay = 0
    connection_type = 'display'

    def get_devices(self):
        display_devices = {}
        x_screen = 0
        hdmi_port = {'hdmi_0' : 2}
        rpi_type = GPIO.RPI_INFO.get('TYPE')
        # RPI 3B+ response on for booth hdmi port
        if 'Pi 4' in rpi_type:
            hdmi_port.update({'hdmi_1': 7})

        for hdmi in hdmi_port:
            power_state_hdmi = Vcgencmd().display_power_state(hdmi_port.get(hdmi))
            if power_state_hdmi == 'on':
                iot_device = {
                    'identifier': hdmi,
                    'name': 'Display hdmi ' + str(x_screen),
                    'x_screen': str(x_screen),
                }
                display_devices[hdmi] = iot_device
                x_screen += 1

        if not len(display_devices):
            # No display connected, create "fake" device to be accessed from another computer
            display_devices['distant_display'] = {
                'name': "Distant Display",
            }

        return display_devices
