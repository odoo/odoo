# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import subprocess
import logging

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools.helpers import path_file, writable
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import (
    import_ctypes_library,
    create_ctypes_string_buffer,
)

_logger = logging.getLogger(__name__)

# Check if the Worldline CTEP library exists, download it and set up the linker otherwise
if not path_file('odoo/addons/iot_drivers/iot_handlers/drivers/ctep/libeasyctep.so').exists():
    load_worldline_library_script = path_file('odoo/addons/iot_drivers/tools/load_worldline_library.sh')
    try:
        with writable():
            subprocess.run(["sudo", "sh", load_worldline_library_script], check=True)
    except subprocess.CalledProcessError:
        _logger.exception('An error encountered while downloading / setting up Worldline CTEP library')

easyCTEP = import_ctypes_library('ctep', 'libeasyctep.so')

# CTEPManager* createCTEPManager(void);
easyCTEP.createCTEPManager.restype = ctypes.c_void_p
# int connectedTerminal(CTEPManager* manager, char* terminal_id, std::shared_ptr<ect::CTEPTerminal> terminal)
easyCTEP.connectedTerminal.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p]


class CTEPInterface(Interface):
    _loop_delay = 10
    connection_type = 'ctep'

    def __init__(self):
        super().__init__()
        self.manager = easyCTEP.createCTEPManager()

    def get_devices(self):
        devices = {}
        terminal_id = create_ctypes_string_buffer()
        device = ctypes.c_void_p()
        if easyCTEP.connectedTerminal(self.manager, terminal_id, ctypes.byref(device)):
            devices[terminal_id.value.decode('utf-8')] = device
        return devices
