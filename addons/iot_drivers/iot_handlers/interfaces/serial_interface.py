# Part of Odoo. See LICENSE file for full copyright and licensing details.

from serial.tools.list_ports import comports

from odoo.addons.iot_drivers.tools.system import IS_WINDOWS
from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.main import iot_devices
import logging

_logger = logging.getLogger(__name__)


class SerialInterface(Interface):
    allow_unsupported = True

    def get_devices(self):
        to_remove = set()
        for identifier, driver in iot_devices.items():
            if driver.interface == self.__class__ and not driver.is_alive():
                _logger.warning("Driver for %s is dead (Thread not alive). Forcing removal.", identifier)
                to_remove.add(identifier)

        serial_devices = {
            port.device: {'identifier': port.device}
            for port in comports()
            if (IS_WINDOWS or port.device != '/dev/ttyAMA10') and port.device not in to_remove
            # RPI 5 uses ttyAMA10 as a console serial port for system messages: odoo interprets it as scale -> avoid it
        }

        return serial_devices
