
from enum import Enum, verify, UNIQUE
from functools import cache
import logging
import platform
import os

from odoo.tools import config

_logger = logging.getLogger(__name__)

@verify(UNIQUE)
class IoTSystem(Enum):
    TEST = 'T'
    IOT_BOX = 'L'
    WINDOWS = 'W'

    @classmethod
    @cache
    def get_all_value(cls) -> tuple[str]:
        """
        Return all names of the enum as a tuple.
        """
        return (item.value for item in cls)
    
    @classmethod
    @cache
    def get_all_value_except_me(cls) -> tuple[str]:
        """
        Return all names of the enum except the current instance.
        """
        return tuple(set(cls.get_all_value()) - {IOT_SYSTEM.value})

def determine_iot_system() -> IoTSystem:
    """
    Determine the IoT system based on the platform and environment variables.
    """
    if platform.system() == 'Windows':
        return IoTSystem.WINDOWS
    elif os.uname()[4][:3] == 'arm':
        return IoTSystem.IOT_BOX
    else:
        return IoTSystem.TEST

IOT_SYSTEM = determine_iot_system()

IS_IOT_TEST = IOT_SYSTEM == IoTSystem.TEST
IS_IOT_BOX = IOT_SYSTEM == IoTSystem.IOT_BOX
IS_WINDOWS = IOT_SYSTEM == IoTSystem.WINDOWS

IS_TESTING = config['test_enable']
LOG_LEVEL = logging.WARNING if IS_IOT_TEST and not IS_TESTING else logging.INFO
_logger.log(LOG_LEVEL, f"Detected IoT system: {IOT_SYSTEM.name} ({IOT_SYSTEM.value})")
