"""Operating system-related utilities for the IoT"""

import configparser
import logging
import netifaces
import requests
import secrets
import socket
import subprocess
import sys
import time

from functools import cache
from pathlib import Path
from platform import system, release

from odoo import release as odoo_release

_logger = logging.getLogger(__name__)


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
    import crypt

    def rpi_only(function):
        """Decorator to check if the system is raspberry pi before running the function."""
        return function
else:
    def rpi_only(_):
        """No-op decorator for non raspberry pi systems."""
        return lambda *args, **kwargs: None


def path_file(*args) -> Path:
    """Return the path to the file from `/home/pi` on IoT Box
    or from `odoo` folder on Virtual IoT Box.

    :return: The path to the file
    """
    return Path(sys.path[0]).parent.joinpath(*args)


def git(*args):
    """Run a git command with the given arguments, taking system
    into account.

    :param args: list of arguments to pass to git
    """
    git_executable = 'git' if IS_RPI else path_file('git', 'cmd', 'git.exe')
    command = [git_executable, f'--work-tree={path_file("odoo")}', f'--git-dir={path_file("odoo", ".git")}', *args]

    p = subprocess.run(command, stdout=subprocess.PIPE, text=True, check=False)
    if p.returncode == 0:
        return p.stdout.strip()
    return None


def pip(*args):
    """Run a pip install command with the given arguments, taking
    system into account.

    :param args: list of arguments to pass to pip install
    :return: True if the command was successful, False otherwise
    """
    python_executable = [] if IS_RPI else [path_file('python', 'python.exe'), '-m']
    command = [*python_executable, 'pip', 'install', *args]

    if IS_RPI:
        command.append('--break-system-package')

    p = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    return p.returncode == 0


@cache
def get_version(detailed_version=False):
    if IS_RPI:
        with open('/var/odoo/iotbox_version', encoding='utf-8') as f:
            image_version = f.readline().strip()
    elif IS_WINDOWS:
        # updated manually when big changes are made to the windows virtual IoT
        image_version = '23.11'
    else:
        image_version = 'test'

    version = IOT_CHAR + image_version
    if detailed_version:
        # Note: on windows IoT, the `release.version` finish with the build date
        version += f"-{odoo_release.version}"
        if IS_RPI:
            commit_hash = git("rev-parse", "--short", "HEAD")
            version += f'#{commit_hash or "unknown"}'

    return version


def get_img_name():
    major, minor = get_version()[1:].split('.')
    return f'iotboxv{major}_{minor}.zip'


def check_image():
    """Check if the current image of IoT Box is up to date

    :return: dict containing major and minor versions of the latest image available
    :rtype: dict
    """
    try:
        response = requests.get('https://nightly.odoo.com/master/iotbox/SHA1SUMS.txt', timeout=5)
        response.raise_for_status()
        data = response.text
    except requests.exceptions.HTTPError:
        _logger.exception('Could not reach the server to get the latest image version')
        return False

    current, latest = '', ''
    hashes = {}
    for line in data.splitlines():
        if not line.strip():
            continue
        value, name = line.split('  ')
        hashes[value] = name
        if name == 'iotbox-latest.zip':
            latest = value
        elif name == get_img_name():
            current = value
    if current == latest:
        return False

    version = (
        hashes.get(latest, 'Error')
        .removeprefix('iotboxv')
        .removesuffix('.zip')
        .split('_')
    )
    return {'major': version[0], 'minor': version[1]}


def update_conf(values, section='iot.box'):
    """Update odoo.conf with the given key and value.

    :param dict values: key-value pairs to update the config with.
    :param str section: The section to update the key-value pairs in (Default: iot.box).
    """
    _logger.debug("Updating odoo.conf with values: %s", values)
    conf = get_conf()

    if not conf.has_section(section):
        _logger.debug("Creating new section '%s' in odoo.conf", section)
        conf.add_section(section)

    for key, value in values.items():
        conf.set(section, key, value) if value else conf.remove_option(section, key)

    with open(path_file("odoo.conf"), "w", encoding='utf-8') as f:
        conf.write(f)


def get_conf(key=None, section='iot.box'):
    """Get the value of the given key from odoo.conf, or the full config if no key is provided.

    :param key: The key to get the value of.
    :param section: The section to get the key from (Default: iot.box).
    :return: The value of the key provided or None if it doesn't exist, or full conf object if no key is provided.
    """
    conf = configparser.RawConfigParser()
    conf.read(path_file("odoo.conf"))

    return conf.get(section, key, fallback=None) if key else conf  # Return the key's value or the configparser object


def _get_identifier():
    if IS_RPI:
        with open('/sys/firmware/devicetree/base/serial-number', encoding='utf-8') as f:
            return f.readline().strip("\x00")
    elif IS_TEST:
        return 'test_identifier'

    # On windows, get motherboard's uuid (serial number isn't reliable as it's not always present)
    command = ['powershell', '-Command', "(Get-CimInstance Win32_ComputerSystemProduct).UUID"]
    p = subprocess.run(command, stdout=subprocess.PIPE, check=False)
    identifier = get_conf('generated_identifier')  # Fallback identifier if windows does not return mb UUID
    if p.returncode == 0 and p.stdout.decode().strip():
        return p.stdout.decode().strip()

    _logger.error("Failed to get Windows IoT serial number, defaulting to a random identifier")
    if not identifier:
        identifier = secrets.token_hex()
        update_conf({'generated_identifier': identifier})

    return identifier


def _get_system_uptime():
    if not IS_RPI:
        return 0
    with open("/proc/uptime", encoding='utf-8') as f:
        return float(f.readline().split()[0])


def is_ngrok_enabled():
    """Check if a ngrok tunnel is active on the IoT Box"""
    try:
        response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
        response.raise_for_status()
        response.json()
        return True
    except (requests.exceptions.RequestException, ValueError):
        # if the request fails or the response is not valid JSON,
        # it means ngrok is not enabled or not running
        _logger.debug("Ngrok isn't running.", exc_info=True)
        return False


def toggle_remote_connection(token=""):
    """Enable/disable remote connection to the IoT Box using ngrok.
    If the token is provided, it will set up ngrok with the
    given authtoken, else it will disable the ngrok service.

    :param str token: The ngrok authtoken to use for the connection"""
    _logger.info("Toggling remote connection with token: %s...", token[:5] if token else "<No Token>")
    p = subprocess.run(
        ['sudo', 'ngrok', 'config', 'add-authtoken', token, '--config', '/home/pi/ngrok.yml'],
        check=False,
    )
    if p.returncode == 0:
        subprocess.run(
            ['sudo', 'systemctl', 'restart' if token else "stop", 'odoo-ngrok.service'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return True
    return False


@rpi_only
def generate_password():
    """Generate an unique code to secure raspberry pi """
    alphabet = 'abcdefghijkmnpqrstuvwxyz23456789'
    password = ''.join(secrets.choice(alphabet) for _ in range(12))
    try:
        shadow_password = crypt.crypt(password, crypt.mksalt())
        subprocess.run(('sudo', 'usermod', '-p', shadow_password, 'pi'), check=True)
        subprocess.run(('sudo', 'cp', '/etc/shadow', '/root_bypass_ramdisks/etc/shadow'), check=True)
        return password
    except subprocess.CalledProcessError as e:
        _logger.exception("Failed to generate password: %s", e.output)
        return 'Error: Check IoT log'


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))  # Google DNS
        return s.getsockname()[0]
    except OSError as e:
        _logger.warning("Could not get local IP address: %s", e)
        return None
    finally:
        s.close()


def get_mac_address():
    interfaces = netifaces.interfaces()
    for interface in map(netifaces.ifaddresses, interfaces):
        if interface.get(netifaces.AF_INET):
            addr = interface.get(netifaces.AF_LINK)[0]['addr']
            if addr != '00:00:00:00:00:00':
                return addr
    return None


NGINX_PATH = path_file('nginx')

if IS_WINDOWS and NGINX_PATH:
    def start_nginx_server():
        _logger.info('Start Nginx server: %s\\nginx.exe', NGINX_PATH)
        subprocess.Popen([str(NGINX_PATH / 'nginx.exe')], cwd=str(NGINX_PATH))
elif IS_RPI:
    def start_nginx_server():
        subprocess.check_call(["sudo", "service", "nginx", "restart"])
else:
    def start_nginx_server():
        pass


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


def get_gateway():
    """Get the router IP address (default gateway)

    :return: The IP address of the default gateway or None if it can't be determined
    """
    gws = netifaces.gateways()
    default = gws.get("default", {})
    gw = default.get(netifaces.AF_INET)
    if gw:
        return gw[0]
    return None


IOT_IDENTIFIER = _get_identifier()
ODOO_START_TIME = time.monotonic()
SYSTEM_START_TIME = ODOO_START_TIME - _get_system_uptime()
