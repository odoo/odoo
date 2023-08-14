# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from glob import glob

from odoo.addons.hw_drivers.interface import Interface


class SerialInterface(Interface):
    connection_type = 'serial'

    def get_devices(self):
        serial_devices = {}
        for identifier in glob('/dev/serial/by-path/*'):
            serial_devices[identifier] = {
                'identifier': identifier
            }
        return serial_devices
