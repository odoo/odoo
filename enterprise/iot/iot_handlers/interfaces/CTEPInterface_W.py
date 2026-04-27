# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
from pathlib import Path
import os
import logging

from odoo.addons.hw_drivers.interface import Interface
from odoo.addons.hw_drivers.tools.helpers import download_from_url, unzip_file
from odoo.addons.hw_drivers.iot_handlers.lib.ctypes_terminal_driver import import_ctypes_library, create_ctypes_string_buffer

_logger = logging.getLogger(__name__)

libPath = Path('odoo/addons/hw_drivers/iot_handlers/lib')
easyCTEPPath = libPath / 'ctep_w/libeasyctep.dll'
zipPath = str(libPath / 'ctep_w.zip')

if not easyCTEPPath.exists():
    download_from_url('http://nightly.odoo.com/master/posbox/iotbox/worldline-ctepv23_02_w.zip', zipPath)
    unzip_file(zipPath, str(libPath / 'ctep_w'))

# Add Worldline dll path so that the linker can find the required dll files
os.environ['PATH'] = str(libPath / 'ctep_w') + os.pathsep + os.environ['PATH']
easyCTEP = import_ctypes_library("ctep_w", "libeasyctep.dll")

easyCTEP.createCTEPManager.restype = ctypes.c_void_p
easyCTEP.connectedTerminal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]


class CTEPInterface(Interface):
    _loop_delay = 10
    connection_type = 'ctep'

    def __init__(self):
        super(CTEPInterface, self).__init__()
        try:
            self.manager = easyCTEP.createCTEPManager()
        except OSError:
            _logger.exception("Failed to initalize CTEPManager")

    def get_devices(self):
        devices = {}
        terminal_id = create_ctypes_string_buffer()
        try:
            if self.manager and easyCTEP.connectedTerminal(self.manager, terminal_id):
                devices[terminal_id.value.decode('utf-8')] = self.manager
        except OSError:
            _logger.exception("Failed to check if the Worldline terminal is connected")
        return devices
