# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from gatt import Device
import logging

from odoo.addons.hw_drivers.driver import Driver
from odoo.addons.hw_drivers.event_manager import event_manager
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.iot_handlers.interfaces.BTInterface_L import bt_devices

_logger = logging.getLogger(__name__)


class SylvacBtDriver(Driver):
    connection_type = 'bluetooth'

    def __init__(self, identifier, device):
        super(SylvacBtDriver, self).__init__(identifier, device)
        self.gatt_device = GattSylvacBtDriver(mac_address=device.mac_address, manager=device.manager)
        self.gatt_device.btdriver = self
        self.gatt_device.connect()
        self.device_type = 'device'
        self.device_connection = 'bluetooth'
        self.device_name = device.alias()

    @classmethod
    def supported(cls, device):
        try:
            if device.alias() in ["SY295", "SY304", "SY276"]:
                return True
        except dbus.exceptions.DBusException as e:
            _logger.warning(e.get_dbus_name())
            _logger.warning(e.get_dbus_message())
        return False

    def disconnect(self):
        super(SylvacBtDriver, self).disconnect()
        del bt_devices[self.device_identifier]


class GattSylvacBtDriver(Device):
    btdriver = False

    def services_resolved(self):
        super().services_resolved()

        device_information_service = next(
            s for s in self.services
            if s.uuid == '00005000-0000-1000-8000-00805f9b34fb')

        measurement_characteristic = next(
            c for c in device_information_service.characteristics if c.uuid == '00005020-0000-1000-8000-00805f9b34fb')
        measurement_characteristic.enable_notifications()

    def characteristic_value_updated(self, characteristic, value):
        total = value[0] + value[1] * 256 + value[2] * 256 * 256 + value[3] * 256 * 256 * 256
        if total > 256 ** 4 / 2:
            total = total - 256 ** 4
        self.btdriver.data['value'] = total / 1000000.0
        event_manager.device_changed(self.btdriver)

    def characteristic_enable_notification_succeeded(self):
        print("Success pied à coulisse Bluetooth!")

    def characteristic_enable_notification_failed(self):
        print("Problem connecting")

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        self.btdriver.disconnect()
