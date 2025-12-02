# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection, IPPError
from itertools import groupby
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
import re
import time

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.main import iot_devices

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

        # get and adjust configuration of printers already added in cups
        for printer_name, printer in printers.items():
            path = printer.get('device-uri')
            if path and printer_name != self.get_identifier(path):
                device_class = 'direct' if 'usb' in path else 'network'
                printer.update({
                    'already-configured': True,
                    'device-class': device_class,
                    'device-make-and-model': printer_name,  # give name set in Cups
                    'device-id': '',
                })
                devices.update({printer_name: printer})

        # filter devices (both added and not added in cups) to show as detected by the IoT Box
        for path, device in devices.items():
            identifier, device = self.process_device(path, device)

            url_is_supported = any(protocol in device["url"] for protocol in ['dnssd', 'lpd', 'socket'])
            model_is_valid = device["device-make-and-model"] != "Unknown"
            printer_is_usb = "direct" in device["device-class"]

            if (url_is_supported and model_is_valid) or printer_is_usb:
                discovered_devices.update({identifier: device})

                if not device.get("already-configured"):
                    self.set_up_printer_in_cups(device)

        # Let get_devices be called again every 20 seconds (get_devices of PrinterInterface
        # takes between 4 and 15 seconds) but increase the delay to 2 minutes if it has been
        # running for more than 1 hour
        if self.start_time and time.time() - self.start_time > 3600:
            self._loop_delay = 120
            self.start_time = None  # Reset start_time to avoid changing the loop delay again

        return self.deduplicate_printers(discovered_devices)

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
        return re.sub(r'[:\/\.\\ ]|(uuid=)|(serial=)', '', path)

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
            already_registered_identifier = next((
                identifier for identifier, device in iot_devices.items()
                if device.device_type == 'printer' and ip and ip == device.ip
            ), None)
            if already_registered_identifier:
                result.append({'identifier': already_registered_identifier})
                continue

            printers_with_same_ip = sorted(printers_with_same_ip, key=lambda printer: printer['identifier'])
            if ip is None or len(printers_with_same_ip) == 1:
                result += printers_with_same_ip
                continue

            chosen_printer = next((
                printer for printer in printers_with_same_ip
                if 'CMD:' in printer['device-id'] or 'ZPL' in printer['device-id']
            ), None)
            if not chosen_printer:
                chosen_printer = printers_with_same_ip[0]
            result.append(chosen_printer)

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

    @staticmethod
    def set_up_printer_in_cups(device):
        """Configure detected printer in cups: ppd files, name, info, groups, ...

        :param dict device: printer device to configure in cups (detected but not added)
        """
        fallback_model = device.get('device-make-and-model', "")
        model = next((
            device_id.split(":")[1] for device_id in device.get('device-id', "").split(";")
            if any(key in device_id for key in ['MDL', 'MODEL'])
        ), fallback_model)
        model = re.sub(r"[\(].*?[\)]", "", model).strip()

        ppdname_argument = next(({"ppdname": ppd} for ppd in PPDs if model and model in PPDs[ppd]['ppd-product']), {})

        try:
            with cups_lock:
                conn.addPrinter(name=device['identifier'], device=device['url'], **ppdname_argument)
                conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
                conn.enablePrinter(device['identifier'])
                conn.acceptJobs(device['identifier'])
                conn.setPrinterUsersAllowed(device['identifier'], ['all'])
                conn.addPrinterOptionDefault(device['identifier'], "usb-no-reattach", "true")
                conn.addPrinterOptionDefault(device['identifier'], "usb-unidir", "true")
        except IPPError:
            _logger.exception("Failed to add printer '%s'", device['identifier'])

    def start(self):
        super().start()
        self.start_zeroconf_listener()
        self.monitor_for_printers()
