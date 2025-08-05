# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection
from itertools import groupby
from re import sub
from threading import Lock
from urllib.parse import urlsplit, parse_qs, unquote
from zeroconf import (
    IPVersion,
    ServiceBrowser,
    ServiceStateChange,
    Zeroconf,
)
import logging
import pyudev
import time

from odoo.addons.iot_drivers.interface import Interface

_logger = logging.getLogger(__name__)

conn = CupsConnection()
PPDs = conn.getPPDs()
cups_lock = Lock()  # We can only make one call to Cups at a time


class PrinterInterface(Interface):
    connection_type = 'printer'
    _loop_delay = 20  # Default delay between calls to get_devices

    def __init__(self):
        super().__init__()
        self.start_time = time.time()

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
        discovered_devices = self.deduplicate_printers(discovered_devices)

        # Let get_devices be called again every 20 seconds (get_devices of PrinterInterface
        # takes between 4 and 15 seconds) but increase the delay to 2 minutes if it has been
        # running for more than 1 hour
        if self.start_time and time.time() - self.start_time > 3600:
            self._loop_delay = 120
            self.start_time = None  # Reset start_time to avoid changing the loop delay again

        return discovered_devices

    def process_device(self, path, device):
        identifier = self.get_identifier(path)
        device.update({
            'identifier': identifier,
            'url': path,
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

    def get_ip(self, device_path):
        hostname = urlsplit(device_path).hostname

        if hostname and hostname.endswith(".local"):
            zeroconf_name = unquote(hostname.lower()) + "."
            if zeroconf_name in self.printer_ip_map:
                return self.printer_ip_map[zeroconf_name]

        return hostname

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

    @staticmethod
    def deduplicate_printers(discovered_printers):
        result = []
        sorted_printers = sorted(discovered_printers.values(), key=lambda printer: str(printer.get('ip')))

        for ip, printers_with_same_ip in groupby(sorted_printers, lambda printer: printer.get('ip')):
            printers_with_same_ip = sorted(printers_with_same_ip, key=lambda printer: printer['identifier'])
            if ip is None or len(printers_with_same_ip) == 1:
                result += printers_with_same_ip
                continue

            device_id = ''
            for printer in printers_with_same_ip:
                if 'CMD:' in printer['device-id'] or 'ZPL' in printer['device-id']:
                    device_id = printer.get('device-id')
                if 'passthru' in printer['identifier'].lower():
                    printers_with_same_ip.remove(printer)
                    continue

            printers_with_same_ip[0]['device-id'] = device_id
            result.append(printers_with_same_ip[0])

        return {printer['identifier']: printer for printer in result}

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

    def start_zeroconf_listener(self):
        self.printer_ip_map = {}
        service_types = [
            "_printer._tcp.local.",
            "_pdl-datastream._tcp.local.",
            "_ipp._tcp.local.",
            "_ipps._tcp.local.",
        ]

        def on_service_change(zeroconf, service_type, name, state_change):
            if state_change is not ServiceStateChange.Added:
                return
            info = zeroconf.get_service_info(service_type, name)
            if info and info.addresses:
                address = info.parsed_addresses(IPVersion.V4Only)[0]
                self.printer_ip_map[name.lower()] = address

        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.zeroconf_browser = ServiceBrowser(zeroconf, service_types, handlers=[on_service_change])

    def start(self):
        super().start()
        self.start_zeroconf_listener()
        self.monitor_for_printers()
