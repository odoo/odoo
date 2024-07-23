# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import serial.tools.list_ports

from odoo.addons.hw_drivers.interface import Interface


class SerialInterface(Interface):
    connection_type = 'serial'

    def get_devices(self):
        serial_ports = serial.tools.list_ports.comports()
        serial_devices = {
            port.device: {'identifier': port.device}
            for port in serial_ports
            if port.subsystem != 'amba'
            # RPI 5 uses ttyAMA10 as a console serial port for system messages: odoo interprets it as scale -> avoid it
        }
        return serial_devices
