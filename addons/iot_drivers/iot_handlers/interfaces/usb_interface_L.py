# Part of Odoo. See LICENSE file for full copyright and licensing details.

from usb import core

from odoo.addons.iot_drivers.interface import Interface


class USBInterface(Interface):
    connection_type = 'usb'
    allow_unsupported = True

    @staticmethod
    def usb_matcher(dev):
        # USB Class codes documentation: https://www.usb.org/defined-class-codes
        # Ignore USB hubs (9) and printers (7)
        if dev.bDeviceClass in [7, 9]:
            return False
        # If the device has generic base class (0) check its interface descriptor
        elif dev.bDeviceClass == 0:
            for conf in dev:
                for interface in conf:
                    if interface.bInterfaceClass == 7:  # 7 = printer
                        return False

        # Ignore serial adapters
        try:
            return dev.product != "USB2.0-Ser!"
        except ValueError:
            return True

    def get_devices(self):
        """
        USB devices are identified by a combination of their `idVendor` and
        `idProduct`. We can't be sure this combination in unique per equipment.
        To still allow connecting multiple similar equipments, we complete the
        identifier by a counter. The drawbacks are we can't be sure the equipments
        will get the same identifiers after a reboot or a disconnect/reconnect.
        """
        usb_devices = {}
        devs = core.find(find_all=True, custom_match=self.usb_matcher)
        cpt = 2
        for dev in devs:
            identifier = "usb_%04x:%04x" % (dev.idVendor, dev.idProduct)
            if identifier in usb_devices:
                identifier += '_%s' % cpt
                cpt += 1
            usb_devices[identifier] = dev
        return usb_devices
