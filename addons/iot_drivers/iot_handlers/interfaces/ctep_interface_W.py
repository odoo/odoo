# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import os
import logging

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools.helpers import download_from_url, unzip_file
from odoo.addons.iot_drivers.tools.system import path_file
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import (
    import_ctypes_library,
    create_ctypes_string_buffer
)

_logger = logging.getLogger(__name__)

libPath = path_file('odoo/addons/iot_drivers/iot_handlers/drivers')
easyCTEPPath = libPath / 'ctep_w/libeasyctep.dll'
zipPath = libPath / 'ctep_w.zip'

if not easyCTEPPath.exists():
    download_from_url('https://nightly.odoo.com/master/posbox/iotbox/worldline-ctepv23_02_w.zip', zipPath)
    unzip_file(zipPath, libPath / 'ctep_w')

# Add Worldline dll path so that the linker can find the required dll files
os.environ['PATH'] = str(libPath / 'ctep_w') + os.pathsep + os.environ['PATH']
easyCTEP = import_ctypes_library("ctep_w", "libeasyctep.dll")

easyCTEP.createCTEPManager.restype = ctypes.c_void_p
easyCTEP.connectedTerminal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]


class CTEPInterface(Interface):
    _loop_delay = 10
    connection_type = 'ctep'

    def __init__(self):
        super().__init__()
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
