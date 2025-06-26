"""Operating system-related utilities for the IoT"""

from platform import system

IOT_SYSTEM = system()

IOT_RPI_CHAR, IOT_WINDOWS_CHAR = "L", "W"

IS_RPI = IOT_SYSTEM[0] == IOT_RPI_CHAR
IS_WINDOWS = IOT_SYSTEM[0] == IOT_WINDOWS_CHAR

if IS_RPI:
    def rpi_only(function):
        """Decorator to check if the system is raspberry pi before running the function."""
        return function
else:
    def rpi_only(_):
        """No-op decorator for non raspberry pi systems."""
        return lambda *args, **kwargs: None
