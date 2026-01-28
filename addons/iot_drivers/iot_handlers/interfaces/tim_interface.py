# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import os
import logging
import subprocess

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools import helpers, system
from odoo.addons.iot_drivers.tools.system import IS_WINDOWS, IS_RPI, path_file
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import CTYPES_BUFFER_SIZE, import_ctypes_library

_logger = logging.getLogger(__name__)


def _configure_tim_lib(lib_name: str) -> bool:
    """Check if the Six TIM library exists, download it and set up
    the linker otherwise.

    :param lib_name: Name of the TIM library file.
    :return: True if the library was successfully configured, False otherwise.
    """
    drivers_path = path_file("odoo/addons/iot_drivers/iot_handlers/drivers")
    source_zip_name = "six-timapiv25_10_l.zip" if IS_RPI else "six-timapiv25_10_w.zip"
    if (drivers_path / "tim" / lib_name).exists():
        return True
    zip_path = drivers_path / "ctep.zip"
    helpers.download_from_url(f"https://download.odoo.com/master/posbox/iotbox/{source_zip_name}", zip_path)
    helpers.unzip_file(zip_path, drivers_path)

    # Make TIM SDK dependency libraries visible for the linker
    if IS_WINDOWS:
        os.environ['PATH'] = str(drivers_path / "tim") + os.pathsep + os.environ['PATH']
        return True

    tim_api_lib = 'libtimapi.so.3'
    tim_api_lib_v = f'{tim_api_lib}.38.0-5308'
    try:
        subprocess.run(["sudo", "cp", drivers_path / "tim" / tim_api_lib_v, "/usr/lib"], check=True)
        subprocess.run(["sudo", "ln", "-fs", f"/usr/lib/{tim_api_lib_v}", f"/usr/lib/{tim_api_lib}"], check=True)
    except subprocess.CalledProcessError as e:
        _logger.error("Failed to link the TIM SDK dependent library: %s", e.output)
    return True


class TIMInterface(Interface):
    _loop_delay = 30
    connection_type = 'tim'
    tid = None

    def __init__(self):
        super().__init__()
        lib_name = 'libsix_odoo_w.dll' if IS_WINDOWS else 'libsix_odoo_l.so'
        if not _configure_tim_lib(lib_name):
            _logger.error("Failed to configure Six TIM library")
            return

        self.tim_api = import_ctypes_library(self.connection_type, lib_name)

        # void *six_initialize_manager(int buffer_size) {
        self.tim_api.six_initialize_manager.argtypes = [ctypes.c_int]
        self.tim_api.six_initialize_manager.restype = ctypes.c_void_p

        # int six_setup_terminal_settings(t_terminal_manager *terminal_manager, char *terminal_id);
        self.tim_api.six_setup_terminal_settings.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        # int six_terminal_connected(t_terminal_manager *terminal_manager);
        self.tim_api.six_terminal_connected.argtypes = [ctypes.c_void_p]

        try:
            buffer_size = ctypes.c_int(CTYPES_BUFFER_SIZE)
            self.manager = self.tim_api.six_initialize_manager(buffer_size)
        except OSError:
            _logger.exception("Failed to initialize TIM manager")

    def get_devices(self):
        if not self.manager:
            _logger.error('Failed to allocate memory for TIM Manager')
            return {}

        new_tid = system.get_conf("six_payment_terminal")

        # If the Six TID setup has changed, reset the settings
        if new_tid != self.tid:
            self.tid = new_tid
            encoded_tid = new_tid.encode() if new_tid else None
            try:
                if not self.tim_api.six_setup_terminal_settings(self.manager, encoded_tid):
                    return {}
            except OSError:
                _logger.exception("Failed to setup Six terminal settings")
                return {}

        # Check if the terminal is online and responsive
        try:
            if self.tid and self.tim_api.six_terminal_connected(self.manager):
                return {
                    self.tid: {
                        "manager": self.manager,
                        "terminal": self.tim_api,
                    }
                }
        except OSError:
            _logger.exception("Failed to check if the Six terminal is connected")

        return {}
