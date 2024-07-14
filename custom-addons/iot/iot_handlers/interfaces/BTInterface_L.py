from gatt import DeviceManager as Gatt_DeviceManager
import dbus
from gi.repository import GLib
import logging
from threading import Thread

from odoo.addons.hw_drivers.interface import Interface
from odoo.addons.hw_drivers.main import iot_devices

bt_devices = {}

_logger = logging.getLogger(__name__)

class GattBtManager(Gatt_DeviceManager):
    def device_discovered(self, device):
        identifier = "bt_%s" % device.mac_address
        if identifier not in bt_devices:
            device.manager = self
            bt_devices[identifier] = device

    def run(self):
        """ Override gatt.DeviceManager.run() method
        to avoid calling GObject.MainLoop() deprecated method inside it.
        MainLoop.run() will 'infinite loop' until MainLoop.quit()
        method is called which we never do, so we don't need to reimplement
        the rest of the MainLoop.run() method """

        if self._main_loop:
            return

        self._interface_added_signal = self._bus.add_signal_receiver(
            self._interfaces_added,
            dbus_interface='org.freedesktop.DBus.ObjectManager',
            signal_name='InterfacesAdded')

        self._properties_changed_signal = self._bus.add_signal_receiver(
            self._properties_changed,
            dbus_interface=dbus.PROPERTIES_IFACE,
            signal_name='PropertiesChanged',
            arg0='org.bluez.Device1',
            path_keyword='path')

        def disconnect_signals():
            for device in self._devices.values():
                device.invalidate()
            self._properties_changed_signal.remove()
            self._interface_added_signal.remove()

        self._main_loop = GLib.MainLoop()
        try:
            self._main_loop.run()
            disconnect_signals()
        except Exception:
            disconnect_signals()
            raise

class BtManager(Thread):
    def run(self):
        dm = GattBtManager(adapter_name='hci0')
        for device in [device_con for device_con in dm.devices() if device_con.is_connected()]:
            device.disconnect()
        dm.start_discovery()
        dm.run()

class BTInterface(Interface):
    connection_type = 'bluetooth'

    def get_devices(self):
        return bt_devices.copy()

bm = BtManager()
bm.daemon = True
bm.start()
