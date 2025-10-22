"""Operating system-related utilities for the IoT"""

import subprocess
from platform import system, release

IOT_SYSTEM = system()

IOT_RPI_CHAR, IOT_WINDOWS_CHAR, IOT_TEST_CHAR = "L", "W", "T"

IS_WINDOWS = IOT_SYSTEM[0] == IOT_WINDOWS_CHAR
IS_RPI = 'rpi' in release()
IS_TEST = not IS_RPI and not IS_WINDOWS
"""IoT system "Test" correspond to any non-Raspberry Pi nor windows system.
Expected to be Linux or macOS used locally for development purposes."""

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


def mtr(host):
    """Run mtr command to the given host to get both
    packet loss (%) and average latency (ms).

    Note: we use ``-4`` in order to force IPv4, to avoid
    empty results on IPv6 networks.

    :param host: The host to ping.
    :return: A tuple of (packet_loss, avg_latency) or (None, None) if the command failed.
    """
    if IS_WINDOWS:
        return None, None

    # sudo is required for probe interval < 1s, which almost divides execution time by 2
    command = ["sudo", "mtr", "-r", "-C", "--no-dns", "-c", "3", "-i", "0.2", "-4", "-G", "1", host]
    p = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=False)
    if p.returncode != 0:
        return None, None

    output = p.stdout.strip()
    last_line = output.splitlines()[-1].split(",")
    try:
        return float(last_line[6]), float(last_line[10])
    except (IndexError, ValueError):
        return None, None
