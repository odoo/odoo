# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from threading import Lock
from cups import IPPError, IPP_JOB_COMPLETED, IPP_JOB_PROCESSING, IPP_JOB_PENDING, CUPS_FORMAT_AUTO, Connection
import logging
import netifaces as ni
import time

from odoo import http
from odoo.addons.iot_drivers.connection_manager import connection_manager
from odoo.addons.iot_drivers.controllers.proxy import proxy_drivers
from odoo.addons.iot_drivers.iot_handlers.drivers.printer_driver_base import PrinterDriverBase
from odoo.addons.iot_drivers.main import iot_devices
from odoo.addons.iot_drivers.tools import helpers, wifi, route

_logger = logging.getLogger(__name__)


class PrinterDriver(PrinterDriverBase):

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.conn = Connection()
        self.cups_lock = Lock()
        self.device_connection = device['device-class'].lower()
        self.receipt_protocol = 'star' if 'STR_T' in device['device-id'] else 'escpos'
        self.connected_by_usb = self.device_connection == 'direct'
        self.device_name = device['device-make-and-model']
        self.ip = device.get('ip')

        if any(cmd in device['device-id'] for cmd in ['CMD:STAR;', 'CMD:ESC/POS;']) or "tm-m30" in self.device_name.lower():
            self.device_subtype = "receipt_printer"
        elif any(cmd in device['device-id'] for cmd in ['COMMAND SET:ZPL;', 'CMD:ESCLABEL;']) or "zpl" in self.device_name.lower():
            self.device_subtype = "label_printer"
        else:
            self.device_subtype = "office_printer"

        self.print_status()

    @classmethod
    def supported(cls, device):
        return True

    def disconnect(self):
        self.send_status('disconnected', 'Printer was disconnected')
        super().disconnect()

    def print_raw(self, data, action_unique_id=None):
        """Print raw data to the printer

        :param data: The data to print
        :param action_unique_id: The unique identifier of the action triggering the print
        """
        try:
            with self.cups_lock:
                job_id = self.conn.createJob(self.device_identifier, 'Odoo print job', {'document-format': CUPS_FORMAT_AUTO})
                self.conn.startDocument(self.device_identifier, job_id, 'Odoo print job', CUPS_FORMAT_AUTO, 1)
                self.conn.writeRequestData(data, len(data))
                self.conn.finishDocument(self.device_identifier)
            self.job_ids.append(job_id)
            if action_unique_id:
                self.job_action_ids[job_id] = action_unique_id
        except IPPError:
            _logger.exception("Printing failed")
            self.send_status(status='error', message='ERROR_FAILED')
            raise  # ensure error caught in driver.py -> don't register action_unique_id

    @classmethod
    def format_star(cls, im):
        width = int((im.width + 7) / 8)

        raster_init = b'\x1b\x2a\x72\x41'
        raster_page_length = b'\x1b\x2a\x72\x50\x30\x00'
        raster_send = b'\x62'
        raster_close = b'\x1b\x2a\x72\x42'

        raster_data = b''
        dots = im.tobytes()
        while len(dots):
            raster_data += raster_send + width.to_bytes(2, 'little') + dots[:width]
            dots = dots[width:]

        return raster_init + raster_page_length + raster_data + raster_close

    @classmethod
    def _get_iot_status(cls):
        identifier = helpers.get_identifier()
        mac_address = helpers.get_mac_address()
        pairing_code = connection_manager.pairing_code
        ssid = wifi.get_access_point_ssid() if wifi.is_access_point() else wifi.get_current()

        ips = []
        for iface_id in ni.interfaces():
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if 'addr' in conf and conf['addr'] not in ['127.0.0.1', '10.11.12.1']:
                    ips.append(conf['addr'])

        return {"identifier": identifier, "mac_address": mac_address, "pairing_code": pairing_code, "ssid": ssid, "ips": ips}

    def print_status(self, data=None):
        """Prints the status ticket of the IoT Box on the current printer.

        :param data: If not None, it means that it has been called from the action route, meaning
        that no matter the connection type, the printer should print the status ticket.
        """
        if not self.connected_by_usb and not data:
            return
        if self.device_subtype == "receipt_printer":
            self.print_status_receipt()
        elif self.device_subtype == "label_printer":
            self.print_status_zpl()
        else:
            title, body = self._printer_status_content()
            self.print_raw(title + b'\r\n' + body.decode().replace('\n', '\r\n').encode())

    def print_status_receipt(self):
        """Prints the status ticket of the IoT Box on the current printer."""
        title, body = self._printer_status_content()

        commands = self.RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
        title = commands['title'] % title
        self.print_raw(commands['center'] + title + b'\n' + body + commands['cut'])

    def print_status_zpl(self):
        iot_status = self._get_iot_status()

        title = "IoT Box Connected" if helpers.get_odoo_server_url() else "IoT Box Status"
        command = f"^XA^CI28 ^FT35,40 ^A0N,30 ^FD{title}^FS"
        p = 85
        if iot_status["pairing_code"]:
            command += f"^FT35,{p} ^A0N,25 ^FDGo to the IoT app, click \"Connect\",^FS"
            p += 35
            command += f"^FT35,{p} ^A0N,25 ^FDPairing code: {iot_status['pairing_code']}^FS"
            p += 35
        if iot_status["ssid"]:
            command += f"^FT35,{p} ^A0N,25 ^FDWi-Fi: {iot_status['ssid']}^FS"
            p += 35
        if iot_status["identifier"]:
            command += f"^FT35,{p} ^A0N,25 ^FDIdentifier: {iot_status['identifier']}^FS"
            p += 35
        if iot_status["ips"]:
            command += f"^FT35,{p} ^A0N,25 ^FDIP: {', '.join(iot_status['ips'])}^FS"
            p += 35
        command += "^XZ"

        self.print_raw(command.encode())

    def _printer_status_content(self):
        """Formats the status information of the IoT Box into a title and a body.

        :return: The title and the body of the status ticket
        :rtype: tuple of bytes
        """
        wlan = identifier = homepage = pairing_code = mac_address = ""
        iot_status = self._get_iot_status()

        wan_quality = helpers.check_network("www.odoo.com")
        to_gateway_quality = helpers.check_network()
        to_printer_quality = helpers.check_network(self.ip) if self.ip else None

        if iot_status["pairing_code"]:
            pairing_code = (
                '\nOdoo not connected\n'
                'Go to the IoT app, click "Connect",\n'
                'Pairing Code: %s\n' % iot_status["pairing_code"]
            )

        if iot_status['ssid']:
            wlan = '\nWireless network:\n%s\n' % iot_status["ssid"]

        ips = iot_status["ips"]
        if len(ips) == 0:
            ip = (
                "\nERROR: Could not connect to LAN\n\nPlease check that the IoT Box is correc-\ntly connected with a "
                "network cable,\n that the LAN is setup with DHCP, and\nthat network addresses are available"
            )
        elif len(ips) == 1:
            ip = '\nIoT Box IP Address:\n%s\n' % ips[0]
        else:
            ip = '\nIoT Box IP Addresses:\n%s\n' % '\n'.join(ips)

        if len(ips) == 0:
            network_quality = ""
        else:
            network_quality = "\nNetwork quality:\n - To Odoo server: %s\n" % wan_quality
            if to_gateway_quality:
                network_quality += " - To Modem: %s\n" % to_gateway_quality
            if to_printer_quality:
                network_quality += " - To Printer (%s): %s\n" % (self.ip, to_printer_quality)

        if len(ips) >= 1:
            identifier = '\nIdentifier:\n%s\n' % iot_status["identifier"]
            mac_address = '\nMac Address:\n%s\n' % iot_status["mac_address"]
            homepage = '\nIoT Box Homepage:\nhttp://%s:8069\n' % ips[0]

        title = b'IoT Box Connected' if helpers.get_odoo_server_url() else b'IoT Box Status'
        body = pairing_code + wlan + identifier + mac_address + ip + network_quality + homepage

        return title, body.encode()

    def _action_default(self, data):
        _logger.debug("_action_default called for printer %s", self.device_name)
        self.print_raw(b64decode(data['document']), action_unique_id=data.get('action_unique_id'))
        return {'print_id': data['print_id']} if 'print_id' in data else {}

    def _cancel_job_with_error(self, job_id, error_message):
        self.job_ids.remove(job_id)
        self.conn.cancelJob(job_id)
        self.send_status(
            status='error', message=error_message, action_unique_id=self.job_action_ids.pop(job_id, None)
        )

    def _check_job_status(self, job_id):
        try:
            with self.cups_lock:
                job = self.conn.getJobAttributes(job_id, requested_attributes=['job-state', 'job-state-reasons', 'job-printer-state-message', 'time-at-creation'])
                _logger.debug("job details for job id #%d: %s", job_id, job)
                job_state = job['job-state']
                if job_state == IPP_JOB_COMPLETED:
                    self.job_ids.remove(job_id)
                    self.job_action_ids.pop(job_id, None)
                    self.send_status(status='success')
                # Generic timeout, e.g. USB printer has been unplugged
                elif job['time-at-creation'] + self.job_timeout_seconds < time.time():
                    self._cancel_job_with_error(job_id, 'ERROR_TIMEOUT')
                # Cannot reach network printer
                elif job_state == IPP_JOB_PROCESSING and 'printer is unreachable' in job.get('job-printer-state-message', ''):
                    self._cancel_job_with_error(job_id, 'ERROR_UNREACHABLE')
                # Any other failure state
                elif job_state not in [IPP_JOB_PROCESSING, IPP_JOB_PENDING]:
                    self._cancel_job_with_error(job_id, 'ERROR_UNKNOWN')
        except IPPError:
            _logger.exception('IPP error occurred while fetching CUPS jobs')
            self.job_ids.remove(job_id)
            self._recent_action_ids.pop(self.job_action_ids.pop(job_id, None), None)


class PrinterController(http.Controller):

    @route.iot_route('/hw_proxy/default_printer_action', type='jsonrpc', cors='*')
    def default_printer_action(self, data):
        printer = next((d for d in iot_devices if iot_devices[d].device_type == 'printer' and iot_devices[d].device_connection == 'direct'), None)
        if printer:
            try:
                iot_devices[printer].action(data)
                return True
            except Exception:  # noqa: BLE001
                return False
        return False


proxy_drivers['printer'] = PrinterDriver
