"""Operating system-related utilities for the IoT"""

from platform import system, release

from odoo.tools import config

IOT_SYSTEM = system()

IOT_RPI_CHAR, IOT_WINDOWS_CHAR, IOT_TEST_CHAR = "L", "W", "T"

IS_WINDOWS = IOT_SYSTEM[0] == IOT_WINDOWS_CHAR
IS_RPI = 'rpi' in release()
IS_TEST = not IS_RPI and not IS_WINDOWS
"""IoT system "Test" correspond to any non-Raspberry Pi nor windows system.
Expected to be Linux or macOS used locally for development purposes."""

IS_TESTING = config['test_enable']
"""True if odoo is running in test mode"""

IOT_CHAR = IOT_RPI_CHAR if IS_RPI else IOT_WINDOWS_CHAR if IS_WINDOWS else IOT_TEST_CHAR
"""IoT system character used in the identifier and version.
- 'L' for Raspberry Pi
- 'W' for Windows
- 'T' for Test (non-Raspberry Pi nor Windows)"""

if IS_RPI:
    def rpi_only(function):
        """Decorator to check if the system is raspberry pi before running the function."""
        return function
else:
    def rpi_only(_):
        """No-op decorator for non raspberry pi systems."""
        return lambda *args, **kwargs: None
