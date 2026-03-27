# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from base64 import b64decode
from datetime import datetime, timezone
import io
import subprocess
import win32print
import pywintypes
import ghostscript

from odoo.addons.iot_drivers.controllers.proxy import proxy_drivers
from odoo.addons.iot_drivers.iot_handlers.drivers.printer_driver_base import PrinterDriverBase
from odoo.addons.iot_drivers.tools import helpers
from odoo.tools.mimetypes import guess_mimetype
from odoo.addons.iot_drivers.iot_handlers.interfaces.printer_interface_W import win32print_lock

_logger = logging.getLogger(__name__)


class PrinterDriver(PrinterDriverBase):

    def __init__(self, identifier, device):
        super().__init__(identifier, device)
        self.device_connection = self._compute_device_connection(device)
        self.device_name = device.get('identifier')
        self.printer_handle = device.get('printer_handle')

        self.receipt_protocol = 'escpos'
        if any(cmd in device['identifier'] for cmd in ['STAR', 'Receipt']):
            self.device_subtype = "receipt_printer"
        elif "ZPL" in device['identifier']:
            self.device_subtype = "label_printer"
        else:
            self.device_subtype = "office_printer"

    @classmethod
    def supported(cls, device):
        return True

    @staticmethod
    def _compute_device_connection(device):
        return 'direct' if device['port'].startswith(('USB', 'TMUSB', 'COM', 'LPT')) else 'network'

    def disconnect(self):
        self.send_status('disconnected', 'Printer was disconnected')
        super().disconnect()

    def print_raw(self, data, action_unique_id=None):
        job_id = False
        page_started = False
        try:
            with win32print_lock:
                job_id = win32print.StartDocPrinter(self.printer_handle, 1, ('', None, "RAW"))
                win32print.StartPagePrinter(self.printer_handle)
                page_started = True
                win32print.WritePrinter(self.printer_handle, data)
                win32print.EndPagePrinter(self.printer_handle)
                win32print.EndDocPrinter(self.printer_handle)
                self.job_ids.append(job_id)
                if action_unique_id:
                    self.job_action_ids[job_id] = action_unique_id
        except pywintypes.error as error:
            _logger.error("Error while printing raw data to printer %s: %s", self.device_name, error)
            if job_id or page_started:
                try:
                    with win32print_lock:
                        if page_started:
                            win32print.EndPagePrinter(self.printer_handle)
                        if job_id:
                            win32print.EndDocPrinter(self.printer_handle)
                            self.job_ids.append(job_id)
                            if action_unique_id:
                                self.job_action_ids[job_id] = action_unique_id
                except pywintypes.error as err:
                    _logger.error("Error while finalizing print job to printer %s after failure: %s", self.device_name, err)
                    self.send_status(status='error', message='ERROR_FAILED')
                    raise

    def print_report(self, data):
        with win32print_lock:
            file_name = helpers.path_file('document.pdf')
            file_name.write_bytes(data)
            sumatra_pdf_path = helpers.path_file("SumatraPDF") / "SumatraPDF.exe"
            use_sumatra = sumatra_pdf_path.exists()

            args = [
                str(sumatra_pdf_path),
                "-print-to",
                self.device_name,
                str(file_name),
                "-silent",
                "-print-settings",
                "duplex"
            ] if use_sumatra else [
                "-dPrinted", "-dBATCH", "-dNOPAUSE", "-dNOPROMPT",
                "-q",
                "-sDEVICE#mswinpr2",
                f'-sOutputFile#%printer%{self.device_name}',
                f'{file_name}'
            ]

            _logger.debug("Printing report with %s using %s", "SumatraPDF" if use_sumatra else "Ghostscript", args)
            if use_sumatra:
                try:
                    subprocess.run(args, check=True)
                    self.send_status(status='success')
                except subprocess.CalledProcessError as error:
                    _logger.exception("Error while printing report, SumatraPDF args: %s, exit code: %s", args, error.returncode)
            else:
                stderr_buf = io.BytesIO()
                stdout_buf = io.BytesIO()
                stdout_log_level = logging.DEBUG
                try:
                    ghostscript.Ghostscript(*args, stdout=stdout_buf, stderr=stderr_buf)
                    self.send_status(status='success')
                except Exception:
                    _logger.exception("Error while printing report, ghostscript args: %s, error buffer: %s", args, stderr_buf.getvalue())
                    stdout_log_level = logging.ERROR  # some stdout value might contains relevant error information
                    self.send_status(status='error', message='ERROR_FAILED')
                    raise
                finally:
                    _logger.log(stdout_log_level, "Ghostscript stdout: %s", stdout_buf.getvalue())

    def _action_default(self, data):
        _logger.debug("_action_default called for printer %s", self.device_name)

        document = b64decode(data['document'])
        mimetype = guess_mimetype(document)
        action_unique_id = data.get('action_unique_id')
        if mimetype == 'application/pdf':
            self.print_report(document)
        else:
            self.print_raw(document, action_unique_id=action_unique_id)
        _logger.debug("_action_default finished with mimetype %s for printer %s", mimetype, self.device_name)
        return {'print_id': data['print_id']} if 'print_id' in data else {}

    def print_status(self, _data=None):
        """Prints the status ticket of the IoT Box on the current printer.

        :param _data: dict provided by the action route
        """
        if self.device_subtype == "receipt_printer":
            commands = self.RECEIPT_PRINTER_COMMANDS[self.receipt_protocol]
            self.print_raw(commands['center'] + (commands['title'] % b'IoT Box Test Receipt') + commands['cut'])
        elif self.device_type == "label_printer":
            self.print_raw("^XA^CI28 ^FT35,40 ^A0N,30 ^FDIoT Box Test Label^FS^XZ".encode())  # noqa: UP012
        else:
            self.print_raw("IoT Box Test Page".encode())  # noqa: UP012

    def _cancel_job_with_error(self, job_id, error_message):
        self.job_ids.remove(job_id)
        win32print.SetJob(self.printer_handle, job_id, 0, None, win32print.JOB_CONTROL_DELETE)
        self.send_status(
            status='error', message=error_message, action_unique_id=self.job_action_ids.pop(job_id, None)
        )

    def _check_job_status(self, job_id):
        try:
            job = win32print.GetJob(self.printer_handle, job_id, win32print.JOB_INFO_1)
            elapsed_time = datetime.now(timezone.utc) - job['Submitted']
            _logger.debug('job details for job id #%d: %s', job_id, job)
            if job['Status'] & win32print.JOB_STATUS_PRINTED:
                self.job_ids.remove(job_id)
                self.job_action_ids.pop(job_id, None)
                self.send_status(status='success')
            # Print timeout, e.g. network printer is disconnected
            if elapsed_time.seconds > self.job_timeout_seconds:
                self._cancel_job_with_error(job_id, 'ERROR_TIMEOUT')
            # Generic error, e.g. USB printer is not connected
            elif job['Status'] & win32print.JOB_STATUS_ERROR:
                self._cancel_job_with_error(job_id, 'ERROR_UNKNOWN')
        except pywintypes.error as error:
            # GetJob returns error 87 (incorrect parameter) if the print job doesn't exist.
            # Windows deletes print jobs on completion, so this actually means the print
            # was succcessful.
            if error.winerror == 87:
                self.send_status(status='success')
            else:
                _logger.exception('Win32 error occurred while querying print job')
            self.job_ids.remove(job_id)
            self._recent_action_ids.pop(self.job_action_ids.pop(job_id, None), None)


proxy_drivers['printer'] = PrinterDriver
