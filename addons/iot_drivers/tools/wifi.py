"""Module to manage Wi-Fi connections and access point mode using
NetworkManager and ``nmcli`` tool.
"""

import base64
from io import BytesIO
import logging
import qrcode
import re
import secrets
import subprocess
import time
from pathlib import Path
from functools import cache

from .helpers import get_ip, get_identifier, get_conf

_logger = logging.getLogger(__name__)

START = True
STOP = False


def _nmcli(args, sudo=False):
    """Run nmcli command with given arguments and return the output.

    :param args: Arguments to pass to nmcli
    :param sudo: Run the command with sudo privileges
    :return: Output of the command
    :rtype: str
    """
    command = ['nmcli', '-t', *args]
    if sudo:
        command = ['sudo', *command]

    p = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    if p.returncode == 0:
        return p.stdout.decode().strip()
    return None


def _scan_network():
    """Scan for connected/available networks and return the SSID.

    :return: list of found SSIDs with a flag indicating whether it's the connected network
    :rtype: list[tuple[bool, str]]
    """
    ssids = _nmcli(['-f', 'ACTIVE,SSID', 'dev', 'wifi'], sudo=True)
    ssids_dict = {
        ssid.split(':')[-1]: ssid.startswith('yes:')
        for ssid in sorted(ssids.splitlines())
        if ssid
    } if ssids else {}
    _logger.debug("Found networks: %s", ssids_dict)

    return [(status, ssid) for ssid, status in ssids_dict.items()]


def _reload_network_manager():
    """Reload the NetworkManager service.
    Can be useful when ``nmcli`` doesn't respond correctly (e.g. can't fetch available
    networks properly).

    :return: True if the service is reloaded successfully
    :rtype: bool
    """
    if subprocess.run(['sudo', 'systemctl', 'reload', 'NetworkManager'], check=False).returncode == 0:
        return True
    else:
        _logger.error('Failed to reload NetworkManager service')
        return False


def get_current():
    """Get the SSID of the currently connected network, or None if it is not connected

    :return: The connected network's SSID, or None
    :rtype: str | None
    """
    nmcli_output = _nmcli(['-f', 'GENERAL.CONNECTION,GENERAL.STATE', 'dev', 'show', 'wlan0'])
    if not nmcli_output:
        return None

    ssid_match = re.match(r'GENERAL\.CONNECTION:(\S+)\n', nmcli_output)
    if not ssid_match:
        return None

    return ssid_match[1] if '(connected)' in nmcli_output else None


def get_available_ssids():
    """Get the SSIDs of the available networks. May reload NetworkManager service
    if the list doesn't contain all the available networks.

    :return: List of available SSIDs
    :rtype: list[str]
    """
    ssids = _scan_network()

    # If the list contains only the connected network, reload network manager and rescan
    if len(ssids) == 1 and is_current(ssids[0][1]) and _reload_network_manager():
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
    _nmcli(['con', 'down', ssid], sudo=True)

    if not get_ip():
        toggle_access_point(START)
    return not is_current(ssid)


def _connect(ssid, password):
    """Disables access point mode and connects to the given
    network using the provided password.

    :param str ssid: SSID of the network to connect to
    :param str password: Password of the network to connect to
    :return: True if connected successfully
    """
    if ssid not in get_available_ssids() or not toggle_access_point(STOP):
        return False

    _logger.info('Connecting to network %s', ssid)
    _nmcli(['device', 'wifi', 'connect', ssid, 'password', password], sudo=True)

    if not _validate_configuration(ssid):
        _logger.warning('Failed to make network configuration persistent for %s', ssid)

    return is_current(ssid)


def reconnect(ssid=None, password=None, force_update=False):
    """Reconnect to the given network. If a connection to the network already exists,
    we can reconnect to it without providing the password (e.g. after a reboot).
    If no SSID is provided, we will try to reconnect to the last connected network.

    :param str ssid: SSID of the network to reconnect to (optional)
    :param str password: Password of the network to reconnect to (optional)
    :param bool force_update: Force connection, even if internet is already available through ethernet
    :return: True if reconnected successfully
    """
    if not force_update:
        timer = time.time() + 10  # Required on boot: wait 10 sec (see: https://github.com/odoo/odoo/pull/187862)
        while time.time() < timer:
            if get_ip():
                if is_access_point():
                    toggle_access_point(STOP)
                return True
            time.sleep(.5)

    if not ssid:
        return toggle_access_point(START)

    should_start_access_point_on_failure = is_access_point() or not get_ip()

    # Try to re-enable an existing connection, or set up a new persistent one
    if toggle_access_point(STOP) and not _nmcli(['con', 'up', ssid], sudo=True):
        _connect(ssid, password)

    connected_successfully = is_current(ssid)
    if not connected_successfully and should_start_access_point_on_failure:
        toggle_access_point(START)

    return connected_successfully


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
    source_path = Path(f'/etc/NetworkManager/system-connections/{ssid}.nmconnection')
    if not source_path.exists():
        return False

    destination_path = Path('/root_bypass_ramdisks') / source_path.relative_to('/')

    # Copy the configuration file to the root filesystem
    if subprocess.run(['sudo', 'cp', source_path, destination_path], check=False).returncode == 0:
        return True
    else:
        _logger.error('Failed to apply the network configuration to /root_bypass_ramdisks.')
        return False


# -------------------------- #
# Access Point Configuration #
# -------------------------- #

@cache
def get_access_point_ssid():
    """Generate a unique SSID for the access point.
    Uses the identifier of the device or a random token if the
    identifier was not found.

    :return: Generated SSID
    :rtype: str
    """
    return "IoTBox-" + get_identifier() or secrets.token_hex(8)


def _configure_access_point(on=True):
    """Update the ``hostapd`` configuration file with the given SSID.
    This method also adds/deletes a static IP address to the ``wlan0`` interface,
    mandatory to allow people to connect to the access point.

    :param bool on: Start or stop the access point
    :return: True if the configuration is successful
    """
    ssid = get_access_point_ssid()

    if on:
        _logger.info("Starting access point with SSID %s", ssid)
        with open('/etc/hostapd/hostapd.conf', 'w', encoding='utf-8') as f:
            f.write(f"interface=wlan0\nssid={ssid}\nchannel=1\n")
    mode = 'add' if on else 'del'
    return (
        subprocess.run(
            ['sudo', 'ip', 'address', mode, '10.11.12.1/24', 'dev', 'wlan0'], check=False, stderr=subprocess.DEVNULL
        ).returncode == 0
        or not on  # Don't fail if stopping access point: IP address might not exist
    )


def toggle_access_point(state=START):
    """Start or stop an access point.

    :param bool state: Start or stop the access point
    :return: True if the operation on the access point is successful
    :rtype: bool
    """
    if not _configure_access_point(state):
        return False

    mode = 'start' if state else 'stop'
    _logger.info("%sing access point.", mode.capitalize())
    if subprocess.run(['sudo', 'systemctl', mode, 'hostapd'], check=False).returncode == 0:
        return True
    else:
        _logger.error("Failed to %s access point.", mode)
        return False


def is_access_point():
    """Check if the device is currently in access point mode.

    :return: True if the device is in access point mode
    :rtype: bool
    """
    return subprocess.run(
        ['systemctl', 'is-active', 'hostapd'], stdout=subprocess.DEVNULL, check=False
    ).returncode == 0


@cache
def generate_qr_code_image(qr_code_data):
    """Generate a QR code based on data argument and return it in base64 image format
    Cached to avoir regenerating the same QR code multiple times

    :param str qr_code_data: Data to encode in the QR code
    :return: The QR code image in base64 format ready to be used in json format
    """
    qr_code = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=0,
    )
    qr_code.add_data(qr_code_data)

    qr_code.make(fit=True)
    img = qr_code.make_image(fill_color="black", back_color="transparent")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def generate_network_qr_codes():
    """Generate a QR codes for the IoT Box network and its homepage
    and return them in base64 image format in a dictionary

    :return: A dictionary containing the QR codes in base64 format
    :rtype: dict
    """
    qr_code_images = {
        'qr_wifi': None,
        'qr_url': generate_qr_code_image(f'http://{get_ip()}'),
    }

    # Generate QR codes which can be used to connect to the IoT Box Wi-Fi network
    if not is_access_point():
        wifi_ssid = get_conf('wifi_ssid')
        wifi_password = get_conf('wifi_password')
        if wifi_ssid and wifi_password:
            wifi_data = f"WIFI:S:{wifi_ssid};T:WPA;P:{wifi_password};;;"
            qr_code_images['qr_wifi'] = generate_qr_code_image(wifi_data)
    else:
        access_point_data = f"WIFI:S:{get_access_point_ssid()};T:nopass;;;"
        qr_code_images['qr_wifi'] = generate_qr_code_image(access_point_data)

    return qr_code_images
