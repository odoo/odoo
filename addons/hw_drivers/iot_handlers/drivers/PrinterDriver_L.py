# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
from cups import IPPError, IPP_JOB_COMPLETED, IPP_JOB_PROCESSING, IPP_JOB_PENDING, CUPS_FORMAT_AUTO
from escpos import printer
import escpos.exceptions
import logging
import netifaces as ni
import re
import time

from odoo import http
from odoo.addons.hw_drivers.connection_manager import connection_manager
from odoo.addons.hw_drivers.controllers.proxy import proxy_drivers
from odoo.addons.hw_drivers.iot_handlers.drivers.printer_driver_base import PrinterDriverBase
from odoo.addons.hw_drivers.iot_handlers.interfaces.PrinterInterface_L import PPDs, conn, cups_lock
from odoo.addons.hw_drivers.main import iot_devices
from odoo.addons.hw_drivers.tools import helpers, wifi, route

_logger = logging.getLogger(__name__)


class PrinterDriver(PrinterDriverBase):

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_connection = device['device-class'].lower()
        self.receipt_protocol = 'star' if 'STR_T' in device['device-id'] else 'escpos'
        self.connected_by_usb = self.device_connection == 'direct'
        connection_prefix = "[USB] " if self.connected_by_usb else ""
        self.device_name = connection_prefix + device['device-make-and-model']

        if any(cmd in device['device-id'] for cmd in ['CMD:STAR;', 'CMD:ESC/POS;']):
            self.device_subtype = "receipt_printer"
        elif any(cmd in device['device-id'] for cmd in ['COMMAND SET:ZPL;', 'CMD:ESCLABEL;']):
            self.device_subtype = "label_printer"
        else:
            self.device_subtype = "office_printer"

        if self.device_subtype == "receipt_printer" and self.receipt_protocol == 'escpos':
            self._init_escpos(device)

        self.print_status()

    def _init_escpos(self, device):
        if device.get('usb_product'):
            def usb_matcher(usb_device):
                return (
                    usb_device.manufacturer.lower() == device['usb_manufacturer'] and
                    usb_device.product == device['usb_product'] and
                    usb_device.serial_number == device['usb_serial_number']
                )

            self.escpos_device = printer.Usb(usb_args={"custom_match": usb_matcher})
        elif device.get('ip'):
            self.escpos_device = printer.Network(device['ip'], timeout=5)
        else:
            return
        try:
            self.escpos_device.open()
            self.escpos_device.close()
        except escpos.exceptions.Error:
            _logger.exception("Could not initialize escpos class")
            self.escpos_device = None

    @classmethod
    def supported(cls, device):
        if device.get('supported', False):
            return True
        protocol = ['dnssd', 'lpd', 'socket']
        if (
                any(x in device['url'] for x in protocol)
                and device['device-make-and-model'] != 'Unknown'
                or 'direct' in device['device-class']
        ):
            model = cls.get_device_model(device)
            ppd_file = ''
            for ppd in PPDs:
                if model and model in PPDs[ppd]['ppd-product']:
                    ppd_file = ppd
                    break
            with cups_lock:
                if ppd_file:
                    conn.addPrinter(name=device['identifier'], ppdname=ppd_file, device=device['url'])
                else:
                    conn.addPrinter(name=device['identifier'], device=device['url'])

                conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
                conn.enablePrinter(device['identifier'])
                conn.acceptJobs(device['identifier'])
                conn.setPrinterUsersAllowed(device['identifier'], ['all'])
                conn.addPrinterOptionDefault(device['identifier'], "usb-no-reattach", "true")
                conn.addPrinterOptionDefault(device['identifier'], "usb-unidir", "true")
            return True
        return False

    @classmethod
    def get_device_model(cls, device):
        device_model = ""
        if device.get('device-id'):
            for device_id in [device_lo for device_lo in device['device-id'].split(';')]:
                if any(x in device_id for x in ['MDL', 'MODEL']):
                    device_model = device_id.split(':')[1]
                    break
        elif device.get('device-make-and-model'):
            device_model = device['device-make-and-model']
        return re.sub(r"[\(].*?[\)]", "", device_model).strip()

    def disconnect(self):
        self.send_status('disconnected', 'Printer was disconnected')
        super(PrinterDriver, self).disconnect()

    def print_raw(self, data):
        """
        Print raw data to the printer
        :param data: The data to print
        """
        if not self.check_printer_status():
            return

        try:
            with cups_lock:
                job_id = conn.createJob(self.device_identifier, 'Odoo print job', {'document-format': CUPS_FORMAT_AUTO})
                conn.startDocument(self.device_identifier, job_id, 'Odoo print job', CUPS_FORMAT_AUTO, 1)
                conn.writeRequestData(data, len(data))
                conn.finishDocument(self.device_identifier)
            self.job_ids.append(job_id)
        except IPPError:
            _logger.exception("Printing failed")
            self.send_status(status='error', message='ERROR_FAILED')

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
        pairing_code = connection_manager.pairing_code
        ssid = wifi.get_access_point_ssid() if wifi.is_access_point() else wifi.get_current()

        ips = []
        for iface_id in ni.interfaces():
            iface_obj = ni.ifaddresses(iface_id)
            ifconfigs = iface_obj.get(ni.AF_INET, [])
            for conf in ifconfigs:
                if 'addr' in conf and conf['addr'] not in ['127.0.0.1', '10.11.12.1']:
                    ips.append(conf['addr'])

        return {"identifier": identifier, "pairing_code": pairing_code, "ssid": ssid, "ips": ips}

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

        wlan = identifier = homepage = pairing_code = ""
        iot_status = self._get_iot_status()

        if iot_status["pairing_code"]:
            pairing_code = (
                '\nOdoo not connected\n'
                'Go to the IoT app, click "Connect",\n'
                'Pairing Code: %s\n' % iot_status["pairing_code"]
            )

        if iot_status['ssid']:
            wlan = '\nWireless network:\n%s\n\n' % iot_status["ssid"]

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

        if len(ips) >= 1:
            identifier = '\nIdentifier:\n%s\n' % iot_status["identifier"]
            homepage = '\nIoT Box Homepage:\nhttp://%s:8069\n\n' % ips[0]

        title = b'IoT Box Connected' if helpers.get_odoo_server_url() else b'IoT Box Status'
        body = pairing_code + wlan + identifier + ip + homepage

        return title, body.encode()

    def _action_default(self, data):
        _logger.debug("_action_default called for printer %s", self.device_name)
        self.print_raw(b64decode(data['document']))
        return {'print_id': data['print_id']}

    def _cancel_job_with_error(self, job_id, error_message):
        self.job_ids.remove(job_id)
        conn.cancelJob(job_id)
        self.send_status(status='error', message=error_message)

    def _check_job_status(self, job_id):
        try:
            with cups_lock:
                job = conn.getJobAttributes(job_id, requested_attributes=['job-state', 'job-state-reasons', 'job-printer-state-message', 'time-at-creation'])
                _logger.debug("job details for job id #%d: %s", job_id, job)
                job_state = job['job-state']
                if job_state == IPP_JOB_COMPLETED:
                    self.job_ids.remove(job_id)
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


class PrinterController(http.Controller):

    @route.iot_route('/hw_proxy/default_printer_action', type='jsonrpc', cors='*')
    def default_printer_action(self, data):
        printer = next((d for d in iot_devices if iot_devices[d].device_type == 'printer' and iot_devices[d].device_connection == 'direct'), None)
        if printer:
            iot_devices[printer].action(data)
            return True
        return False


proxy_drivers['printer'] = PrinterDriver
