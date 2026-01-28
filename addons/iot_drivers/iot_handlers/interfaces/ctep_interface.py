# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import logging
import os
import subprocess

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools import helpers
from odoo.addons.iot_drivers.tools.system import path_file, IS_RPI, IS_WINDOWS
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import (
    create_ctypes_string_buffer,
    import_ctypes_library,
)

_logger = logging.getLogger(__name__)


def _configure_ctep_lib(lib_name: str) -> bool:
    """Check if the WorldLine CTEP library exists, download it
    and set up the linker otherwise.

    :param lib_name: Name of the CTEP library file.
    :return: True if the library was successfully configured, False otherwise.
    """
    drivers_path = path_file("odoo/addons/iot_drivers/iot_handlers/drivers")
    source_zip_name = "worldline-ctepv21_07.zip" if IS_RPI else "worldline-ctepv23_02_w.zip"
    if (drivers_path / "ctep" / lib_name).exists():
        return True
    zip_path = drivers_path / "ctep.zip"
    helpers.download_from_url(f"https://download.odoo.com/master/posbox/iotbox/{source_zip_name}", zip_path)
    helpers.unzip_file(zip_path, drivers_path)

    if IS_WINDOWS:
        # Add WorldLine dll path so that the linker can find the required dll files
        os.environ['PATH'] = str(drivers_path / 'ctep') + os.pathsep + os.environ['PATH']
        return True

    try:
        worldline_ctep_conf_path = "/etc/ld.so.conf.d/worldline-ctep.conf"
        subprocess.run(
            ["sudo", "tee", worldline_ctep_conf_path, f"/root_bypass_ramdisks{worldline_ctep_conf_path}"],
            text=True,
            input=str(drivers_path / "ctep" / "lib"),
            check=True,
        )
        subprocess.run(["sudo", "ldconfig"], check=True)
        subprocess.run(["sudo", "cp", "/etc/ld.so.cache", "/root_bypass_ramdisks/etc/ld.so.cache"], check=True)
    except subprocess.CalledProcessError:
        _logger.exception("Failed to download and set up WorldLine CTEP library")
        return False
    return True


class CTEPInterface(Interface):
    _loop_delay = 10
    connection_type = 'ctep'

    def __init__(self):
        super().__init__()
        lib_name = "libeasyctep.so" if IS_RPI else "libeasyctep.dll"
        if not _configure_ctep_lib(lib_name):
            _logger.error("Failed to configure Worldline CTEP library")
            return

        self.easy_ctep = import_ctypes_library(self.connection_type, lib_name)
        self.easy_ctep.createCTEPManager.restype = ctypes.c_void_p
        extra_args = [ctypes.c_void_p] if IS_RPI else []
        self.easy_ctep.connectedTerminal.argtypes = [ctypes.c_void_p, ctypes.c_char_p, *extra_args]

        try:
            self.manager = self.easy_ctep.createCTEPManager()
        except OSError:
            _logger.exception("Failed to initalize CTEPManager")

    def get_devices(self):
        terminal_id = create_ctypes_string_buffer()
        device = ctypes.c_void_p()
        extra_args = [ctypes.byref(device)] if IS_RPI else []
        try:
            if self.manager and self.easy_ctep.connectedTerminal(self.manager, terminal_id, *extra_args):
                return {
                    terminal_id.value.decode(): {
                        "manager": device if IS_RPI else self.manager,
                        "terminal": self.easy_ctep,
                    }
                }
        except OSError:
            _logger.exception("Failed to check if the WorldLine terminal is connected")
        return {}
