# Part of Odoo. See LICENSE file for full copyright and licensing details.

from cups import Connection as CupsConnection, IPPError
from itertools import groupby
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
import subprocess
import time

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.main import iot_devices

_logger = logging.getLogger(__name__)


class PrinterInterface(Interface):
    connection_type = 'printer'
    _loop_delay = 20  # Default delay between calls to get_devices

    def __init__(self):
        super().__init__()
        self.start_time = time.time()
        self.printer_devices = {}
        self.conn = CupsConnection()
        self.PPDs = self.conn.getPPDs()

    def get_devices(self):
        # get printers already configured in Cups
        discovered_devices = {
            name: {"identifier": name, "already-configured": True, **printer}
            for name, printer in self.conn.getPrinters().items()
        }

        # Check if new printers available, and configure them if so
        for name, printer in self.conn.getDevices().items():
            identifier, printer = self.process_device(name, printer)

            url_is_supported = bool(re.match(r"^(dnssd|lpd|socket|ipp).+", printer["url"]))
            model_is_valid = printer["device-make-and-model"] != "Unknown"

            if (url_is_supported and model_is_valid) or printer.get("is_usb"):
                discovered_devices.update({identifier: printer})

        # Let get_devices be called again every 20 seconds (get_devices of PrinterInterface
        # takes between 4 and 15 seconds) but increase the delay to 2 minutes if it has been
        # running for more than 1 hour
        if self.start_time and time.time() - self.start_time > 3600:
            self._loop_delay = 120
            self.start_time = None  # Reset start_time to avoid changing the loop delay again

        self.printer_devices.update(self.deduplicate_printers(discovered_devices))

        # Devices previously discovered but not found this call
        # When the printer disconnects it can still be listed in cups and print after reconnecting
        # Wait for 3 consecutive misses before removing it from the list allows us to avoid errors and unnecessary double prints
        missing = set(self.printer_devices) - set(discovered_devices)
        for identifier in missing:
            printer = self.printer_devices[identifier]
            if printer["disconnect_counter"] >= 2:
                _logger.warning('Printer %s not found 3 times in a row, disconnecting.', identifier)
                self.printer_devices.pop(identifier, None)
            else:
                printer["disconnect_counter"] += 1

        return self.printer_devices.copy()

    def process_device(self, path, device):
        identifier = self.get_identifier(path)
        device.update({
            'identifier': identifier,
            'url': path,
            'disconnect_counter': 0,
        })
        if path.startswith("usb"):
            device.update(self.get_usb_info(path))
        else:
            device['ip'] = self.get_ip(path)

        return identifier, device

    def get_identifier(self, path: str):
        """Parse the path to get a valid Cups identifier.
        Removes: ``:``, ``/``, ``.``, ``\\``, ``space``, ``uuid=`` and ``serial=``
        and truncates the string to 127 characters.

        e.g. ``ipp://printers/printer1:1234/abcd`` -> ``ippprintersprinter11234abcd``
        e.g. ``uuid=1234-5678-90ab-cdef`` -> ``1234-5678-90ab-cdef``
        """
        ip = self.get_ip(path)
        if ip:
            mac_address = self.get_mac_from_ip(ip)
            if mac_address:
                path = f"dnssd{mac_address}" if path.startswith("dnssd") else path.replace(ip, mac_address)
        return re.sub(r'[:/.?@\\ ]|(uuid=)|(serial=)', '', unquote(path))[:127]

    def get_ip(self, device_path):
        hostname = urlsplit(device_path).hostname

        if hostname and hostname.endswith(".local"):
            zeroconf_name = unquote(hostname.lower()) + "."
            if zeroconf_name in self.printer_ip_map:
                return self.printer_ip_map[zeroconf_name]

        return hostname

    def get_mac_from_ip(self, ip):
        if not ip:
            return None
        output = subprocess.run(["arp", "-n", ip], capture_output=True, text=True, check=False)
        mac_address_match = re.search(r"\w{2}:\w{2}:\w{2}:\w{2}:\w{2}:\w{2}", output.stdout)
        if mac_address_match:
            return mac_address_match[0]
        return None

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
                "is_usb": True,
            }
        else:
            return {}

    def deduplicate_printers(self, discovered_printers):
        result = []
        sorted_printers = sorted(
            discovered_printers.values(), key=lambda printer: (str(printer.get('ip')), printer["identifier"])
        )

        for ip, printers_with_same_ip in groupby(sorted_printers, lambda printer: printer.get('ip')):
            already_registered_identifier = next((
                identifier for identifier, device in iot_devices.items()
                if device.device_type == 'printer' and ip and ip == device.ip
            ), None)
            if already_registered_identifier:
                result += next(
                    ([p] for p in printers_with_same_ip if p['identifier'] == already_registered_identifier), []
                )
                continue

            printers_with_same_ip = list(printers_with_same_ip)
            is_ipp_ready = any(p['identifier'].startswith("ipp") for p in printers_with_same_ip)
            if ip is None or len(printers_with_same_ip) == 1:
                printers_with_same_ip[0]["is_ipp_ready"] = is_ipp_ready
                result += printers_with_same_ip
                continue

            chosen_printer = next((
                printer for printer in printers_with_same_ip
                if 'CMD:' in printer['device-id'] or 'ZPL' in printer['device-id']
            ), printers_with_same_ip[0])
            chosen_printer["ipp_ready"] = is_ipp_ready
            result.append(chosen_printer)

        return {
            printer["identifier"]: printer
            for printer in result
            if self.set_up_printer_in_cups(printer)
        }

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
                'is_usb': True,
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

    def set_up_printer_in_cups(self, device: dict) -> bool:
        """Configure detected printer in cups: ppd files, name, info, groups, ...

        :param dict device: printer device to configure in cups (detected but not added)
        :return: True if printer is configured in cups, False otherwise
        """
        if device.get("already-configured"):
            return True
        fallback_model = device.get('device-make-and-model', "")
        model = next((
            device_id.split(":")[1] for device_id in device.get('device-id', "").split(";")
            if any(key in device_id for key in ['MDL', 'MODEL'])
        ), fallback_model)
        model = re.sub(r"[\(].*?[\)]", "", model).strip()

        ppdname_argument = next(
            ({"ppdname": ppd} for ppd in self.PPDs if model and model in self.PPDs[ppd]['ppd-product']),
            {"ppdname": "everywhere"} if device.get("ipp_ready") else {}
        )

        try:
            self.conn.addPrinter(name=device['identifier'], device=device['url'], **ppdname_argument)
            self.conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
            self.conn.enablePrinter(device['identifier'])
            self.conn.acceptJobs(device['identifier'])
            self.conn.setPrinterUsersAllowed(device['identifier'], ['all'])
            self.conn.addPrinterOptionDefault(device['identifier'], "usb-no-reattach", "true")
            self.conn.addPrinterOptionDefault(device['identifier'], "usb-unidir", "true")
            return True
        except IPPError:
            _logger.exception("Failed to add printer '%s'", device['identifier'])
            return False

    def start(self):
        super().start()
        self.start_zeroconf_listener()
        self.monitor_for_printers()
