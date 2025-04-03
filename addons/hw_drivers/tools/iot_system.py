
from enum import Enum, unique
import logging
import platform

_logger = logging.getLogger(__name__)


@unique
class IoTSystem(Enum):
    TEST_LOCAL = 'T'
    RASPBERRY_PI = 'L'
    WINDOWS = 'W'


def determine_iot_system():
    """
    Determine the IoT system based on the platform and environment variables.
    """
    if platform.system() == 'Windows':
        return IoTSystem.WINDOWS
    if 'rpi' in platform.release():  # same logic as in the iot requirement.txt
        return IoTSystem.RASPBERRY_PI
    _logger.warning("IoT system detected as local test")
    return IoTSystem.TEST_LOCAL


IOT_SYSTEM = determine_iot_system()
"""IoT system type detected for the current environment"""

IS_TEST_LOCAL = IOT_SYSTEM == IoTSystem.TEST_LOCAL
"""True if the IoT system is a local test environment ->
any system which are not raspberry pi nor Windows"""
IS_RPI = IOT_SYSTEM == IoTSystem.RASPBERRY_PI
IS_WINDOWS = IOT_SYSTEM == IoTSystem.WINDOWS
