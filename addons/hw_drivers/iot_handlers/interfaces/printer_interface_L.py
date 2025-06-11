# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection
from re import sub
from threading import Lock
from urllib.parse import urlsplit, parse_qs
import logging
import pyudev

from odoo.addons.hw_drivers.interface import Interface

_logger = logging.getLogger(__name__)

conn = CupsConnection()
PPDs = conn.getPPDs()
cups_lock = Lock()  # We can only make one call to Cups at a time


class PrinterInterface(Interface):
    _loop_delay = 120
    connection_type = 'printer'
    printer_devices = {}

    def get_devices(self):
        discovered_devices = {}
        with cups_lock:
            printers = conn.getPrinters()
            devices = conn.getDevices()
            for printer_name, printer in printers.items():
                path = printer.get('device-uri', False)
                if printer_name != self.get_identifier(path):
                    device_class = 'direct' if 'usb' in printer.get('device-uri') else 'network'
                    printer.update({
                        'supported': True,
                        'device-class': device_class,
                        'device-make-and-model': printer_name,  # give name set in Cups
                        'device-id': '',
                    })
                    devices.update({printer_name: printer})

        for path, device in devices.items():
            identifier, device = self.process_device(path, device)
            discovered_devices.update({identifier: device})
        self.printer_devices.update(discovered_devices)
        # Deal with devices which are on the list but were not found during this call of "get_devices"
        # If they aren't detected 3 times consecutively, remove them from the list of available devices
        for device in list(self.printer_devices):
            if not discovered_devices.get(device):
                disconnect_counter = self.printer_devices.get(device).get('disconnect_counter')
                if disconnect_counter >= 2:
                    self.printer_devices.pop(device, None)
                else:
                    self.printer_devices[device].update({'disconnect_counter': disconnect_counter + 1})
        return dict(self.printer_devices)

    def process_device(self, path, device):
        identifier = self.get_identifier(path)
        device.update({
            'identifier': identifier,
            'url': path,
            'disconnect_counter': 0,
        })
        if device['device-class'] == 'direct':
            device.update(self.get_usb_info(path))
        elif device['device-class'] == 'network':
            device['ip'] = self.get_ip(path)

        return identifier, device

    def get_identifier(self, path):
        """
        Necessary because the path is not always a valid Cups identifier,
        as it may contain characters typically found in URLs or paths.

          - Removes characters: ':', '/', '.', '\', and space.
          - Removes the exact strings: "uuid=" and "serial=".

        Example 1:
            Input: "ipp://printers/printer1:1234/abcd"
            Output: "ippprintersprinter11234abcd"

        Example 2:
            Input: "uuid=1234-5678-90ab-cdef"
            Output: "1234-5678-90ab-cdef
        """
        return sub(r'[:\/\.\\ ]|(uuid=)|(serial=)', '', path)

    @staticmethod
    def get_ip(device_path):
        return urlsplit(device_path).hostname

    @staticmethod
    def get_usb_info(device_path):
        parsed_url = urlsplit(device_path)
        parsed_query = parse_qs(parsed_url.query)
        manufacturer = parsed_url.hostname
        product = parsed_url.path.removeprefix("/")
        serial = parsed_query["serial"][0] if "serial" in parsed_query else None

        if manufacturer and product and serial:
            return {
                "usb_manufacturer": manufacturer,
                "usb_product": product,
                "usb_serial_number": serial,
            }
        else:
            return {}

    def monitor_for_printers(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by('usb')

        def on_device_change(udev_device):
            if udev_device.action != 'add' or udev_device.driver != 'usblp':
                return

            try:
                device_id = udev_device.attributes.asstring('ieee1284_id')
                manufacturer = udev_device.parent.attributes.asstring('manufacturer')
                product = udev_device.parent.attributes.asstring('product')
                serial = udev_device.parent.attributes.asstring('serial')
            except KeyError as err:
                _logger.warning("Could not hotplug printer, field '%s' is not present", err.args[0])
                return

            path = f"usb://{manufacturer}/{product}?serial={serial}"
            iot_device = {
                'device-class': 'direct',
                'device-make-and-model': f'{manufacturer} {product}',
                'device-id': device_id,
            }
            identifier, iot_device = self.process_device(path, iot_device)
            self.add_device(identifier, iot_device)

        observer = pyudev.MonitorObserver(monitor, callback=on_device_change)
        observer.start()

    def start(self):
        super().start()
        self.monitor_for_printers()
