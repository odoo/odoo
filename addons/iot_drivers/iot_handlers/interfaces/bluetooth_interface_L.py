from gatt import DeviceManager as Gatt_DeviceManager
from gatt.errors import NotReady
import dbus
import dbus.service
from gi.repository import GLib
import logging
from threading import Thread

from odoo.addons.iot_drivers.interface import Interface

_logger = logging.getLogger(__name__)

bluetooth_devices = {}

AGENT_PATH = "/odoo/iot/agent/bluetooth"


class BtPairingAgent(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, AGENT_PATH)

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device): return "000000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device): return dbus.UInt32(0)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device): pass

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self): pass


def _register_pairing_agent():
    try:
        bus = dbus.SystemBus()
        agent = BtPairingAgent(bus)
        agent_manager = dbus.Interface(
            bus.get_object("org.bluez", "/org/bluez"),
            "org.bluez.AgentManager1"
        )
        agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
        agent_manager.RequestDefaultAgent(AGENT_PATH)
        _logger.info("BtPairingAgent: Registered at %s", AGENT_PATH)
        return agent
    except dbus.exceptions.DBusException:
        _logger.exception("BtPairingAgent: Registration failed")


class GattBtManager(Gatt_DeviceManager):
    def device_discovered(self, device):
        identifier = "bt_%s" % device.mac_address
        if identifier not in bluetooth_devices:
            _logger.debug("New device discovered: %s alias=%s", identifier, device.alias())
            device.manager = self
            bluetooth_devices[identifier] = device

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
    def __init__(self):
        super().__init__(daemon=True)

    def run(self):
        self._pairing_agent = _register_pairing_agent()
        dm = GattBtManager(adapter_name='hci0')
        for device in dm.devices():
            if device.is_connected():
                identifier = f"bt_{device.mac_address}"
                _logger.debug("Already connected device found at startup: %s alias=%s", identifier, device.alias())
                device.manager = dm
                bluetooth_devices[identifier] = device
        try:
            dm.start_discovery()
            dm.run()
        except NotReady:
            _logger.error("Bluetooth adapter not ready. Set `is_adapter_powered` to `True` or run 'echo power on | sudo bluetoothctl'")


class BTInterface(Interface):
    connection_type = 'bluetooth'

    def get_devices(self):
        return bluetooth_devices.copy()


bm = BtManager()
bm.start()
