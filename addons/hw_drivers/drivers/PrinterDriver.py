# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64decode
import logging
import subprocess
import tempfile

from odoo import _
from odoo.addons.hw_drivers.controllers.driver import Driver, PPDs, conn, printers

_logger = logging.getLogger(__name__)

class PrinterDriver(Driver):
    connection_type = 'printer'

    def __init__(self, device):
        super(PrinterDriver, self).__init__(device)
        self._device_type = 'printer'
        self._device_connection = self.dev['device-class'].lower()
        self._device_name = self.dev['device-make-and-model']
        self._device_identifier = self.dev['identifier']

    @classmethod
    def supported(cls, device):
        protocol = ['dnssd', 'lpd']
        if any(x in device['url'] for x in protocol) or 'direct' in device['device-class']:
            ppdFile = ''
            for device_id in [device_lo for device_lo in device['device-id'].split(';') if device['device-id']]:
                if any(x in device_id for x in ['MDL','MODEL']):
                    device.update({'MDL': device_id.split(':')[1]})
                    for ppd in PPDs:
                        if device['MDL'] in PPDs[ppd]['ppd-product']:
                            ppdFile = ppd
            if ppdFile:
                conn.addPrinter(name = device['identifier'], ppdname = ppdFile, device = device['url'])
            else:
                conn.addPrinter(name = device['identifier'], device = device['url'])
            if device['identifier'] not in printers:
                conn.setPrinterInfo(device['identifier'], device['device-make-and-model'])
                conn.enablePrinter(device['identifier'])
                conn.acceptJobs(device['identifier'])
                conn.setPrinterUsersAllowed(device['identifier'],['all'])
            else:
                device['device-make-and-model'] = printers[device['identifier']]['printer-info']
            return True
        return False

    def action(self, data):
        try:
            with tempfile.NamedTemporaryFile() as tmp:
                tmp.write(b64decode(data['document']))
                tmp.flush()
                subprocess.check_call("lp -d %s %s" % (self.dev['identifier'], tmp.name), shell=True)
        except subprocess.CalledProcessError as e:
            _logger.warning(e.output)
