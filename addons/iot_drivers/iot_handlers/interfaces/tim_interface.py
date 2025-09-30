# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ctypes
import os
import logging
import subprocess
from platform import system

from odoo.addons.iot_drivers.interface import Interface
from odoo.addons.iot_drivers.tools import helpers
from odoo.tools.misc import file_path
from odoo.addons.iot_drivers.iot_handlers.drivers.ctypes_terminal_driver import import_ctypes_library

_logger = logging.getLogger(__name__)

LIB_PATH = file_path('iot_drivers/iot_handlers/drivers')
DOWNLOAD_URL = 'https://nightly.odoo.com/master/posbox/iotbox/six-timapiv23_09_l.zip'

# Download and unzip timapi library, overwriting the existing one
TIMAPI_ZIP_PATH = f'{LIB_PATH}/tim.zip'
helpers.download_from_url(DOWNLOAD_URL, TIMAPI_ZIP_PATH)
helpers.unzip_file(TIMAPI_ZIP_PATH, f'{LIB_PATH}/tim')

# Make TIM SDK dependency libraries visible for the linker
if system() == 'Windows':
    LIB_PATH = file_path('iot_drivers/iot_handlers/drivers')
    os.environ['PATH'] = file_path('iot_drivers/iot_handlers/drivers/tim') + os.pathsep + os.environ['PATH']
else:
    TIMAPI_DEPENDANCY_LIB = 'libtimapi.so.3'
    TIMAPI_DEPENDANCY_LIB_V = f'{TIMAPI_DEPENDANCY_LIB}.31.1-2272'
    DEP_LIB_PATH = file_path('iot_drivers/iot_handlers/drivers/tim')
    USR_LIB_PATH = '/usr/lib'
    try:
        with helpers.writable():
            subprocess.call([f'sudo cp {DEP_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB_V} {USR_LIB_PATH}'], shell=True)
            subprocess.call(
                [f'sudo ln -fs {USR_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB_V} {USR_LIB_PATH}/{TIMAPI_DEPENDANCY_LIB}'],
                shell=True
            )
    except subprocess.CalledProcessError as e:
        _logger.error("Failed to link the TIM SDK dependent library: %s", e.output)

# Import Odoo Timapi Library
LIB_NAME = 'libsix_odoo_w.dll' if system() == 'Windows' else 'libsix_odoo_l.so'
TIMAPI = import_ctypes_library('tim', LIB_NAME)

# --- Setup library prototypes ---
# void *six_initialize_manager(void);
TIMAPI.six_initialize_manager.restype = ctypes.c_void_p

# int six_setup_terminal_settings(t_terminal_manager *terminal_manager, char *terminal_id);
TIMAPI.six_setup_terminal_settings.argtypes = [ctypes.c_void_p, ctypes.c_char_p]

# int six_terminal_connected(t_terminal_manager *terminal_manager);
TIMAPI.six_terminal_connected.argtypes = [ctypes.c_void_p]


class TIMInterface(Interface):
    _loop_delay = 30
    connection_type = 'tim'

    def __init__(self):
        super().__init__()

        try:
            self.manager = TIMAPI.six_initialize_manager()
        except OSError:
            _logger.exception("Failed to initalize TIM manager")
        if not self.manager:
            _logger.error('Failed to allocate memory for TIM Manager')
        self.tid = None

    def get_devices(self):
        if not self.manager:
            return {}

        # As this code is fetched by the IoT Box from the DB, we can't be sure
        # that the IoT Box has the new method `get_conf`.
        # This try-except should be replaced by a simple call to `get_conf` in master
        try:
            new_tid = helpers.get_conf("six_payment_terminal")
        except AttributeError:
            _logger.warning(
                "Failed to get the Six TID from the configuration file, trying to read it from the old file"
            )
            new_tid = helpers.read_file_first_line('odoo-six-payment-terminal.conf')
        devices = {}

        # If the Six TID setup has changed, reset the settings
        if new_tid != self.tid:
            self.tid = new_tid
            encoded_tid = new_tid.encode() if new_tid else None
            try:
                if not TIMAPI.six_setup_terminal_settings(self.manager, encoded_tid):
                    return {}
            except OSError:
                _logger.exception("Failed to setup Six terminal settings")
                return {}

        # Check if the terminal is online and responsive
        try:
            if self.tid and TIMAPI.six_terminal_connected(self.manager):
                devices[self.tid] = self.manager
        except OSError:
            _logger.exception("Failed to check if the Six terminal is connected")

        return devices
