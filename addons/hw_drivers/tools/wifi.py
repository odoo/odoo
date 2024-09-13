"""Module to manage Wi-Fi connections and access point mode using
NetworkManager and ``nmcli`` tool.
"""

import logging
import subprocess
from pathlib import Path
from functools import cache

from .helpers import get_ip, get_mac_address, writable

__all__ = [
    'access_point',
    'connect',
    'disconnect',
    'get_available_ssids',
    'get_current',
    'is_access_point',
    'is_current',
    'reconnect',
]

_logger = logging.getLogger(__name__)


def _run(sudo=False, *args):
    """Run nmcli command with given arguments and return the output.

    :param sudo: Run the command with sudo privileges
    :param args: Arguments to pass to nmcli
    :return: Output of the command
    :rtype: str or bool
    :raises subprocess.CalledProcessError: If the command fails
    """
    command = ['nmcli', '-t', *args]
    if sudo:
        command = ['sudo', *command]

    try:
        return subprocess.run(command, stdout=subprocess.PIPE, check=True).stdout.decode().strip()
    except subprocess.CalledProcessError:
        return False


def _scan_network():
    """Scan for connected/available networks and return the SSID.

    :return: list of found SSIDs with a flag indicating whether it's the connected network
    :rtype: list[tuple[bool, str]]
    """
    command = ['-f', 'ACTIVE,SSID', 'dev', 'wifi']
    ssids = _run(True, *command)
    return [
        (ssid.startswith('yes:'), ssid.split(':')[-1])
        for ssid in ssids.splitlines()
        if ssid
    ] if ssids else []


def _reload_network_manager():
    """Reload the NetworkManager service.
    Can be useful when ``nmcli`` doesn't respond correctly (e.g. can't fetch available
    networks properly).

    :return: True if the service is reloaded successfully
    :rtype: bool
    """
    try:
        subprocess.run(['sudo', 'systemctl', 'reload', 'NetworkManager'], check=True)
        return True
    except subprocess.CalledProcessError:
        _logger.error('Failed to reload NetworkManager service')
        return False


def get_current():
    """Get the SSID of the currently connected network.
    If no network is connected, generate a unique SSID for the access point.

    :return: The connected network's or access point's SSID
    :rtype: str
    """
    return next((
        ssid for (active, ssid) in _scan_network()
        if active
    ), None)


def get_available_ssids():
    """Get the SSIDs of the available networks. May reload NetworkManager service
    if the list doesn't contain all the available networks.

    :return: List of available SSIDs
    :rtype: list[str]
    """
    ssids = _scan_network()

    # If the list contains only the connected network, reload network manager and rescan
    if len(ssids) == 1 and is_current(ssids[0]) and _reload_network_manager():
        ssids = _scan_network()

    return [ssid for (_, ssid) in ssids]


def is_current(ssid):
    """Check if the given SSID is the one connected."""
    return ssid == get_current()


def disconnect():
    """Disconnects from the current network.

    :return: True if disconnected successfully
    """
    ssid = get_current()

    if not ssid:
        return True

    _logger.info('Disconnecting from network %s', ssid)
    command = ['con', 'down', ssid]
    _run(True, *command)

    return not is_current(ssid)


def _validate_configuration(ssid):
    """For security reasons, everything that is saved in the root filesystem
    on IoT Boxes is lost after reboot. This method saves the network
    configuration file in the right filesystem (``/root_bypass_ramdisks``).

    Although it is not mandatory to connect to the Wi-Fi, this method is required
    for the network to be reconnected automatically after a reboot.

    :param str ssid: SSID of the network to validate
    :return: True if the configuration file is saved successfully
    :rtype: bool
    """
    source_path = Path('/etc/NetworkManager/system-connections/') / f'{ssid}.nmconnection'
    destination_path = Path('/root_bypass_ramdisks') / source_path.relative_to('/')

    if not source_path.exists() or not destination_path.exists():
        return False

    try:
        subprocess.run(['sudo', 'cp', str(source_path), str(destination_path)], check=True)
        return True
    except subprocess.CalledProcessError:
        _logger.error('Failed to copy the network configuration file to root_bypass_ramdisks.')
        return False


def connect(ssid, password):
    """Disables access point mode, disconnects from the current network and
    connects to the given network using the provided password.

    :param str ssid: SSID of the network to connect to
    :param str password: Password of the network to connect to
    :return: True if connected successfully
    """
    if not access_point(on=False) or not disconnect():
        return False

    _logger.info('Connecting to network %s', ssid)
    command = ['device', 'wifi', 'connect', ssid, 'password', password]
    _run(True, *command)

    if not _validate_configuration(ssid):
        _logger.warning('Failed to make network configuration persistent for %s', ssid)

    return is_current(ssid)


def reconnect(ssid=None, password=None):
    """Reconnect to the given network. If a connection to the network already exists,
    we can reconnect to it without providing the password (e.g. after a reboot).
    If no SSID is provided, we will try to reconnect to the last connected network.

    :param str ssid: SSID of the network to reconnect to (optional)
    :param str password: Password of the network to reconnect to (optional)
    :return: True if reconnected successfully
    """
    if get_ip():
        return True

    if not ssid:
        return access_point(True)

    command = ['con', 'up', ssid]
    if not _run(True, *command):
        connect(ssid, password)

    return is_current(ssid) or access_point(on=True)


# --------------------------
# Access Point Configuration
# --------------------------

@cache
def _generate_hostapd_ssid():
    """Generate a unique SSID for the access point.
    Uses the MAC address of the device without the colons.

    :return: Generated SSID
    :rtype: str
    """
    return "IoTBox-" + ''.join(get_mac_address().split(':'))


def _configure_access_point():
    """Update the ``hostapd`` configuration file with the given SSID."""

    ssid = _generate_hostapd_ssid()

    with writable():
        with open('/etc/hostapd/hostapd.conf', 'w', encoding='utf-8') as f:
            f.write(f"interface=wlan0\nssid={ssid}\nchannel=1\n")


def access_point(on=True):
    """Start or stop an access point.

    :param bool on: Start or stop the access point
    :return: True if the operation on the access point is successful
    :rtype: bool
    """
    if on:
        _configure_access_point()

    try:
        _logger.info("Starting access point.")
        command = 'start' if on else 'stop'
        subprocess.run(['sudo', 'systemctl', command, 'hostapd'], check=True)
        return True
    except subprocess.CalledProcessError:
        _logger.error("Failed to start access point.")
        return False


def is_access_point():
    """Check if the device is currently in access point mode.

    :return: True if the device is in access point mode
    :rtype: bool
    """
    command = ['-g', 'device', 'connection', 'show', '--active']
    # We only get the first line as `loopback` can still be active when `wlan0` is
    device = _run(True, *command).splitlines()[0]
    return device == 'loopback'
