# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from re import sub, finditer
import subprocess
import RPi.GPIO as GPIO
import logging

from odoo.addons.hw_drivers.interface import Interface


_logger = logging.getLogger(__name__)

try:
    from vcgencmd import Vcgencmd
except ImportError:
    Vcgencmd = None
    _logger.warning('Could not import library vcgencmd')


class DisplayInterface(Interface):
    _loop_delay = 0
    connection_type = 'display'

    def get_devices(self):

        # If no display connected, create "fake" device to be accessed from another computer
        display_devices = {
             'distant_display' : {
                  'name': "Distant Display",
             },
        }

        if Vcgencmd:
            return self.get_devices_vcgencmd() or display_devices
        else:
            return self.get_devices_tvservice() or display_devices


    def get_devices_tvservice(self):
        display_devices = {}
        displays = subprocess.check_output(['tvservice', '-l']).decode()
        x_screen = 0
        for match in finditer(r'Display Number (\d), type HDMI (\d)', displays):
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

        return display_devices

    def get_devices_vcgencmd(self):
        """
        With the new IoT build 23_11 which uses Raspi OS Bookworm,
        tvservice is no longer usable.
        vcgencmd returns the display power state as on or off of the display whose ID is passed as the parameter.
        The display ID for the preceding three methods are determined by the following table.

        Display        ID
        Main LCD        0
        Secondary LCD   1
        HDMI 0          2
        Composite       3
        HDMI 1          7
        """
        display_devices = {}
        x_screen = 0
        hdmi_port = {'hdmi_0' : 2} # HDMI 0
        rpi_type = GPIO.RPI_INFO.get('TYPE')
        # Check if it is a RPI 3B+ beacause he response on for booth hdmi port
        if 'Pi 4' in rpi_type:
            hdmi_port.update({'hdmi_1': 7}) # HDMI 1

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

        return display_devices
