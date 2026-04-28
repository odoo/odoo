# Part of Odoo. See LICENSE file for full copyright and licensing details.

import dbus
from gi.repository import GLib
from gatt import Device
import logging

from odoo.addons.iot_drivers.iot_handlers.interfaces.bluetooth_interface_L import bluetooth_devices
from odoo.addons.iot_drivers.driver import Driver
from odoo.addons.iot_drivers.event_manager import event_manager

_logger = logging.getLogger(__name__)


class SylvacBtDriver(Driver):
    connection_type = 'bluetooth'

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.gatt_device = GattSylvacBtDriver(mac_address=device.mac_address, manager=device.manager)
        self.gatt_device.btdriver = self
        self.device_type = 'device'
        self.device_connection = 'bluetooth'
        self.device_name = device.alias()
        self._actions['read_once'] = self._action_read_once
        _logger.info("Sylvac: Driver loading for %s alias=%s", identifier, device.alias())

        self._pair_then_connect(device.mac_address)

    def _pair_then_connect(self, mac_address):
        try:
            bus = dbus.SystemBus()
            path_mac = mac_address.replace(':', '_').upper()
            device_obj = bus.get_object('org.bluez', f"/org/bluez/hci0/dev_{path_mac}")
            props = dbus.Interface(device_obj, 'org.freedesktop.DBus.Properties')
            device_iface = dbus.Interface(device_obj, 'org.bluez.Device1')

            props.Set('org.bluez.Device1', 'Trusted', dbus.Boolean(True))

            if props.Get('org.bluez.Device1', 'Paired'):
                self.gatt_device.connect()
                return

            def on_pair_success():
                _logger.info("Sylvac: Pairing succeeded for %s", mac_address)
                GLib.timeout_add(500, self._do_connect)

            def on_pair_error(error):
                _logger.warning("Pairing error for %s: %s — connecting anyway", mac_address, error)
                GLib.timeout_add(500, self._do_connect)

            device_iface.Pair(reply_handler=on_pair_success, error_handler=on_pair_error)

        except Exception:  # noqa: BLE001
            _logger.exception("_pair_then_connect failed. Connecting anyway")
            self.gatt_device.connect()

    def _do_connect(self):
        _logger.info("Sylvac: Initiating GATT connect to %s", self.gatt_device.mac_address)
        self.gatt_device.connect()
        return False

    def _action_read_once(self, _data):
        """Make value available to the longpolling event route"""
        event_manager.device_changed(self)

    @classmethod
    def supported(cls, device):
        try:
            if device.alias() in ["SY295", "SY304", "SY276"]:
                _logger.info("Sylvac: Device %s is supported (alias=%s)", device.mac_address, device.alias())
                return True
            elif device.alias() == "SY":
                _logger.info(
                    "Sylvac: Device %s should be supported but it appears it's in a faulty state, please reset the bluetooth on the device (alias=%s)",
                    device.mac_address,
                    device.alias(),
                )
        except dbus.exceptions.DBusException as e:
            _logger.warning(e.get_dbus_name())
            _logger.warning(e.get_dbus_message())
        return False

    def disconnect(self):
        super().disconnect()
        del bluetooth_devices[self.device_identifier]


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
        self.btdriver.data['status'] = 'success'
        event_manager.device_changed(self.btdriver)

    def characteristic_enable_notification_succeeded(self):
        _logger.info("Successfully connected to %s", self.device_name)

    def characteristic_enable_notification_failed(self):
        _logger.info("Problem connecting to %s", self.device_name)

    def disconnect_succeeded(self):
        super().disconnect_succeeded()
        self.btdriver.disconnect()
