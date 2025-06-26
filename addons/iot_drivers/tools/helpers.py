# Part of Odoo. See LICENSE file for full copyright and licensing details.

import configparser
from enum import Enum
from functools import cache, wraps
from importlib import util
import inspect
import io
import logging
from pathlib import Path
import re
import requests
import secrets
import subprocess
import socket
from urllib.parse import parse_qs
import urllib3.util
import sys
from threading import Thread, Lock
import time
import zipfile
from werkzeug.exceptions import Locked

from odoo import http, release, service
from odoo.addons.iot_drivers.tools.system import IOT_CHAR, IOT_RPI_CHAR, IOT_WINDOWS_CHAR, IS_RPI, IS_TEST, IS_WINDOWS
from odoo.tools.func import reset_cached_properties
from odoo.tools.misc import file_path

lock = Lock()
_logger = logging.getLogger(__name__)

if IS_RPI:
    import crypt


class Orientation(Enum):
    """xrandr/wlr-randr screen orientation for kiosk mode"""
    NORMAL = 'normal'
    INVERTED = '180'
    LEFT = '90'
    RIGHT = '270'


class IoTRestart(Thread):
    """
    Thread to restart odoo server in IoT Box when we must return a answer before
    """
    def __init__(self, delay):
        Thread.__init__(self)
        self.delay = delay

    def run(self):
        time.sleep(self.delay)
        service.server.restart()


def toggleable(function):
    """Decorate a function to enable or disable it based on the value
    of the associated configuration parameter.
    """
    fname = f"<function {function.__module__}.{function.__qualname__}>"

    @wraps(function)
    def devtools_wrapper(*args, **kwargs):
        if args and args[0].__class__.__name__ == 'DriverController':
            if get_conf('longpolling', section='devtools'):
                _logger.warning("Refusing call to %s: longpolling is disabled by devtools", fname)
                raise Locked("Longpolling disabled by devtools")  # raise to make the http request fail
        elif function.__name__ == 'action':
            action = args[1].get('action', 'default')  # first argument is self (containing Driver instance), second is 'data'
            disabled_actions = (get_conf('actions', section='devtools') or '').split(',')
            if action in disabled_actions or '*' in disabled_actions:
                _logger.warning("Ignoring call to %s: '%s' action is disabled by devtools", fname, action)
                return None
        elif get_conf('general', section='devtools'):
            _logger.warning("Ignoring call to %s: method is disabled by devtools", fname)
            return None

        return function(*args, **kwargs)
    return devtools_wrapper


def require_db(function):
    """Decorator to check if the IoT Box is connected to the internet
    and to a database before executing the function.
    This decorator injects the ``server_url`` parameter if the function has it.
    """
    @wraps(function)
    def wrapper(*args, **kwargs):
        fname = f"<function {function.__module__}.{function.__qualname__}>"
        server_url = get_odoo_server_url()
        iot_box_ip = get_ip()
        if not iot_box_ip or iot_box_ip == "10.11.12.1" or not server_url:
            _logger.info('Ignoring the function %s without a connected database', fname)
            return

        arg_name = 'server_url'
        if arg_name in inspect.signature(function).parameters:
            _logger.debug('Adding server_url param to %s', fname)
            kwargs[arg_name] = server_url

        return function(*args, **kwargs)
    return wrapper


if IS_WINDOWS:
    def start_nginx_server():
        path_nginx = get_path_nginx()
        if path_nginx:
            _logger.info('Start Nginx server: %s\\nginx.exe', path_nginx)
            subprocess.Popen([str(path_nginx / 'nginx.exe')], cwd=str(path_nginx))
elif IS_RPI:
    def start_nginx_server():
        subprocess.check_call(["sudo", "service", "nginx", "restart"])
else:
    def start_nginx_server():
        pass


def check_image():
    """Check if the current image of IoT Box is up to date

    :return: dict containing major and minor versions of the latest image available
    :rtype: dict
    """
    try:
        response = requests.get('https://nightly.odoo.com/master/iotbox/SHA1SUMS.txt', timeout=5)
        response.raise_for_status()
        data = response.content.decode()
    except requests.exceptions.HTTPError:
        _logger.exception('Could not reach the server to get the latest image version')
        return False

    check_file = {}
    value_actual = ''
    for line in data.split('\n'):
        if line:
            value, name = line.split('  ')
            check_file.update({value: name})
            if name == 'iotbox-latest.zip':
                value_latest = value
            elif name == get_img_name():
                value_actual = value
    if value_actual == value_latest:  # pylint: disable=E0601
        return False
    version = check_file.get(value_latest, 'Error').replace('iotboxv', '').replace('.zip', '').split('_')
    return {'major': version[0], 'minor': version[1]}


def save_conf_server(url, token, db_uuid, enterprise_code, db_name=None):
    """
    Save server configurations in odoo.conf
    :param url: The URL of the server
    :param token: The token to authenticate the server
    :param db_uuid: The database UUID
    :param enterprise_code: The enterprise code
    :param db_name: The database name
    """
    update_conf({
        'remote_server': url,
        'token': token,
        'db_uuid': db_uuid,
        'enterprise_code': enterprise_code,
        'db_name': db_name,
    })
    get_odoo_server_url.cache_clear()


def generate_password():
    """
    Generate an unique code to secure raspberry pi
    """
    alphabet = 'abcdefghijkmnpqrstuvwxyz23456789'
    password = ''.join(secrets.choice(alphabet) for i in range(12))
    try:
        shadow_password = crypt.crypt(password, crypt.mksalt())
        subprocess.run(('sudo', 'usermod', '-p', shadow_password, 'pi'), check=True)
        subprocess.run(('sudo', 'cp', '/etc/shadow', '/root_bypass_ramdisks/etc/shadow'), check=True)
        return password
    except subprocess.CalledProcessError as e:
        _logger.exception("Failed to generate password: %s", e.output)
        return 'Error: Check IoT log'


def get_img_name():
    major, minor = get_version()[1:].split('.')
    return 'iotboxv%s_%s.zip' % (major, minor)


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


@cache
def get_identifier():
    if IS_RPI:
        return read_file_first_line('/sys/firmware/devicetree/base/serial-number').strip("\x00")
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


def get_path_nginx():
    return path_file('nginx')


@cache
def get_odoo_server_url():
    """Get the URL of the linked Odoo database.

    :return: The URL of the linked Odoo database.
    :rtype: str or None
    """
    return get_conf('remote_server')


def get_token():
    """:return: The token to authenticate the server"""
    return get_conf('token')


def get_commit_hash():
    return subprocess.run(
        ['git', '--work-tree=/home/pi/odoo/', '--git-dir=/home/pi/odoo/.git', 'rev-parse', '--short', 'HEAD'],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout.decode('ascii').strip()


@cache
def get_version(detailed_version=False):
    if IS_RPI:
        image_version = read_file_first_line('/var/odoo/iotbox_version')
    elif IS_WINDOWS:
        # updated manually when big changes are made to the windows virtual IoT
        image_version = '23.11'
    elif IS_TEST:
        image_version = 'test'

    version = IOT_CHAR + image_version
    if detailed_version:
        # Note: on windows IoT, the `release.version` finish with the build date
        version += f"-{release.version}"
        if IS_RPI:
            version += f'#{get_commit_hash()}'

    return version


def delete_iot_handlers():
    """Delete all drivers, interfaces and libs if any.
    This is needed to avoid conflicts with the newly downloaded drivers.
    """
    try:
        iot_handlers = Path(file_path('iot_drivers/iot_handlers'))
        filenames = [
            f"odoo/addons/iot_drivers/iot_handlers/{file.relative_to(iot_handlers)}"
            for file in iot_handlers.glob('**/*')
            if file.is_file()
        ]
        unlink_file(*filenames)
        _logger.info("Deleted old IoT handlers")
    except OSError:
        _logger.exception('Failed to delete old IoT handlers')


@toggleable
@require_db
def download_iot_handlers(auto=True, server_url=None):
    """Get the drivers from the configured Odoo server.
    If drivers did not change on the server, download
    will be skipped.

    :param auto: If True, the download will depend on the parameter set in the database
    :param server_url: The URL of the connected Odoo database (provided by decorator).
    """
    etag = get_conf('iot_handlers_etag')
    try:
        response = requests.post(
            server_url + '/iot/get_handlers',
            data={'identifier': get_identifier(), 'auto': auto},
            timeout=8,
            headers={'If-None-Match': etag} if etag else None,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        _logger.exception('Could not reach configured server to download IoT handlers')
        return

    data = response.content
    if response.status_code == 304 or not data:
        _logger.info('No new IoT handler to download')
        return

    try:
        update_conf({'iot_handlers_etag': response.headers['ETag'].strip('"')})
    except KeyError:
        _logger.exception('No ETag in the response headers')

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        _logger.exception('Bad IoT handlers response received: not a zip file')
        return

    delete_iot_handlers()
    path = path_file('odoo', 'addons', 'iot_drivers', 'iot_handlers')
    zip_file.extractall(path)


def compute_iot_handlers_addon_name(handler_kind, handler_file_name):
    return "odoo.addons.iot_drivers.iot_handlers.{handler_kind}.{handler_name}".\
        format(handler_kind=handler_kind, handler_name=handler_file_name.removesuffix('.py'))


def load_iot_handlers():
    """
    This method loads local files: 'odoo/addons/iot_drivers/iot_handlers/drivers' and
    'odoo/addons/iot_drivers/iot_handlers/interfaces'
    And execute these python drivers and interfaces
    """
    for directory in ['interfaces', 'drivers']:
        path = file_path(f'iot_drivers/iot_handlers/{directory}')
        filesList = get_handlers_files_to_load(path)
        for file in filesList:
            spec = util.spec_from_file_location(compute_iot_handlers_addon_name(directory, file), str(Path(path).joinpath(file)))
            if spec:
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    _logger.exception('Unable to load handler file: %s', file)
    reset_cached_properties(http.root)


def get_handlers_files_to_load(handler_path):
    """
    Get all handler files that an IoT system should load in a list.
    - Rpi IoT boxes load file without suffixe and _L
    - Windows IoT load file without suffixes and _W
    :param handler_path: The path to the directory containing the files (either drivers or interfaces)
    :return: files corresponding to the current IoT system
    :rtype list:
    """
    if IS_RPI:
        return [x.name for x in Path(handler_path).glob(f'*[!{IOT_WINDOWS_CHAR}].*')]
    elif IS_WINDOWS:
        return [x.name for x in Path(handler_path).glob(f'*[!{IOT_RPI_CHAR}].*')]
    return []


def odoo_restart(delay=0):
    """
    Restart Odoo service
    :param delay: Delay in seconds before restarting the service (Default: 0)
    """
    IR = IoTRestart(delay)
    IR.start()


def path_file(*args):
    """Return the path to the file from IoT Box root or Windows Odoo
    server folder

    :return: The path to the file
    """
    return Path(sys.path[0]).parent.joinpath(*args)


def read_file_first_line(filename):
    path = path_file(filename)
    if path.exists():
        with path.open('r') as f:
            return f.readline().strip('\n')


def unlink_file(*filenames):
    for filename in filenames:
        path = path_file(filename)
        if path.exists():
            path.unlink()


def write_file(filename, text, mode='w'):
    """This function writes 'text' to 'filename' file

    :param filename: The name of the file to write to
    :param text: The text to write to the file
    :param mode: The mode to open the file in (Default: 'w')
    """
    path = path_file(filename)
    with open(path, mode) as f:
        f.write(text)


def download_from_url(download_url, path_to_filename):
    """
    This function downloads from its 'download_url' argument and
    saves the result in 'path_to_filename' file
    The 'path_to_filename' needs to be a valid path + file name
    (Example: 'C:\\Program Files\\Odoo\\downloaded_file.zip')
    """
    try:
        request_response = requests.get(download_url, timeout=60)
        request_response.raise_for_status()
        write_file(path_to_filename, request_response.content, 'wb')
        _logger.info('Downloaded %s from %s', path_to_filename, download_url)
    except requests.exceptions.RequestException:
        _logger.exception('Failed to download from %s', download_url)


def unzip_file(path_to_filename, path_to_extract):
    """
    This function unzips 'path_to_filename' argument to
    the path specified by 'path_to_extract' argument
    and deletes the originally used .zip file
    Example: unzip_file('C:\\Program Files\\Odoo\\downloaded_file.zip', 'C:\\Program Files\\Odoo\\new_folder'))
    Will extract all the contents of 'downloaded_file.zip' to the 'new_folder' location)
    """
    try:
        path = path_file(path_to_filename)
        with zipfile.ZipFile(path) as zip_file:
            zip_file.extractall(path_file(path_to_extract))
        Path(path).unlink()
        _logger.info('Unzipped %s to %s', path_to_filename, path_to_extract)
    except Exception:
        _logger.exception('Failed to unzip %s', path_to_filename)


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


def disconnect_from_server():
    """Disconnect the IoT Box from the server"""
    update_conf({
        'remote_server': '',
        'token': '',
        'db_uuid': '',
        'db_name': '',
        'enterprise_code': '',
        'screen_orientation': '',
        'browser_url': '',
        'iot_handlers_etag': '',
        'last_websocket_message_id': '',
    })
    odoo_restart()


def save_browser_state(url=None, orientation=None):
    """Save the browser state to the file

    :param url: The URL the browser is on (if None, the URL is not saved)
    :param orientation: The orientation of the screen (if None, the orientation is not saved)
    """
    update_conf({
        'browser_url': url,
        'screen_orientation': orientation.name.lower() if orientation else None,
    })


def load_browser_state():
    """Load the browser state from the file

    :return: The URL the browser is on and the orientation of the screen (default to NORMAL)
    """
    url = get_conf('browser_url')
    orientation = get_conf('screen_orientation') or Orientation.NORMAL.name
    return url, Orientation[orientation.upper()]


def url_is_valid(url):
    """Checks whether the provided url is a valid one or not

    :param url: the URL to check
    :return: True if the URL is valid and False otherwise
    :rtype: bool
    """
    try:
        result = urllib3.util.parse_url(url.strip())
        return all([result.scheme in ["http", "https"], result.netloc, result.host != 'localhost'])
    except urllib3.exceptions.LocationParseError:
        return False


def parse_url(url):
    """Parses URL params and returns them as a dictionary starting by the url.
    Does not allow multiple params with the same name (e.g. <url>?a=1&a=2 will return the same as <url>?a=1)

    :param url: the URL to parse
    :return: the dictionary containing the URL and params
    :rtype: dict
    """
    if not url_is_valid(url):
        raise ValueError("Invalid URL provided.")

    url = urllib3.util.parse_url(url.strip())
    search_params = {
        key: value[0]
        for key, value in parse_qs(url.query, keep_blank_values=True).items()
    }
    return {
        "url": f"{url.scheme}://{url.netloc}",
        **search_params,
    }


def reset_log_level():
    """Reset the log level to the default one if the reset timestamp is reached
    This timestamp is set by the log controller in `iot_drivers/homepage.py` when the log level is changed
    """
    log_level_reset_timestamp = get_conf('log_level_reset_timestamp')
    if log_level_reset_timestamp and float(log_level_reset_timestamp) <= time.time():
        _logger.info("Resetting log level to default.")
        update_conf({
            'log_level_reset_timestamp': '',
            'log_handler': ':INFO,werkzeug:WARNING',
            'log_level': 'info',
        })


def _get_system_uptime():
    if not IS_RPI:
        return 0
    uptime_string = read_file_first_line("/proc/uptime")
    return float(uptime_string.split(" ")[0])


def _get_raspberry_pi_model():
    """Returns the Raspberry Pi model number (e.g. 4) as an integer
    Returns 0 if the model can't be determined, or -1 if called on Windows

    :rtype: int
    """
    if not IS_RPI:
        return -1
    with open('/proc/device-tree/model', encoding='utf-8') as model_file:
        match = re.search(r'Pi (\d)', model_file.read())
        return int(match[1]) if match else 0


raspberry_pi_model = _get_raspberry_pi_model()
odoo_start_time = time.monotonic()
system_start_time = odoo_start_time - _get_system_uptime()


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
