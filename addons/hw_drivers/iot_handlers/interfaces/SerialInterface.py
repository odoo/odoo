from glob import glob

from odoo.addons.hw_drivers.controllers.driver import Interface


class SerialInterface(Interface):
    connection_type = 'serial'

    def get_devices(self):
        serial_devices = {}
        for identifier in glob('/dev/serial/by-path/*'):
            serial_devices[identifier] = {
                'identifier': identifier
            }
        return serial_devices
