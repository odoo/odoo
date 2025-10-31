# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import logging
import subprocess

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.tools.system import path_file
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import import_ctypes_library, create_ctypes_string_buffer


_logger = logging.getLogger(__name__)


# Check if the Worldline CTEP library exists, download it and set up the linker otherwise
if not path_file('odoo/addons/iot_drivers/iot_handlers/drivers/ctep/libeasyctep.so').exists():
    extract_path = path_file("odoo/addons/iot_drivers/iot_handlers/drivers/")
    try:
        helpers.download_from_url(
            "https://download.odoo.com/master/posbox/iotbox/worldline-ctepv21_07.zip", extract_path / "ctep.zip"
        )
        helpers.unzip_file(extract_path / "ctep.zip", extract_path)

        worldline_ctep_conf_path = "/etc/ld.so.conf.d/worldline-ctep.conf"
        subprocess.run(
            ["sudo", "tee", worldline_ctep_conf_path, f"/root_bypass_ramdisks{worldline_ctep_conf_path}"],
            text=True,
            input=str(extract_path / "ctep" / "lib"),
            check=True,
        )
        subprocess.run(["sudo", "ldconfig"], check=True)
        subprocess.run(["sudo", "cp", "/etc/ld.so.cache", "/root_bypass_ramdisks/etc/ld.so.cache"], check=True)

    except subprocess.CalledProcessError:
        _logger.exception("Failed to download and set up Worldline CTEP library")


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
