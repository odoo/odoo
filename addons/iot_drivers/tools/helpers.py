# Part of Odoo. See LICENSE file for full copyright and licensing details.

from enum import Enum
from functools import cache, wraps
from importlib import util
from ipaddress import ip_address
import inspect
import io
import logging
from pathlib import Path
import requests
import socket
from urllib.parse import parse_qs
import urllib3.util
from threading import Thread
import time
import zipfile
from werkzeug.exceptions import Locked

from odoo import http, service
from odoo.addons.iot_drivers.tools import system
from odoo.addons.iot_drivers.tools.system import (
    IOT_IDENTIFIER,
    IS_RPI,
    IS_WINDOWS,
    IOT_RPI_CHAR,
    IOT_WINDOWS_CHAR,
)
from odoo.tools.func import reset_cached_properties
from odoo.tools.misc import file_path

_logger = logging.getLogger(__name__)


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
            if system.get_conf('longpolling', section='devtools'):
                _logger.warning("Refusing call to %s: longpolling is disabled by devtools", fname)
                raise Locked("Longpolling disabled by devtools")  # raise to make the http request fail
        elif function.__name__ == 'action':
            action = kwargs.get('action', 'default')  # first argument is self (containing Driver instance), second is 'data'
            disabled_actions = (system.get_conf('actions', section='devtools') or '').split(',')
            if action in disabled_actions or '*' in disabled_actions:
                _logger.warning("Ignoring call to %s: '%s' action is disabled by devtools", fname, action)
                return None
        elif system.get_conf('general', section='devtools'):
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
        iot_box_ip = system.get_ip()
        if not iot_box_ip or iot_box_ip == "10.11.12.1" or not server_url:
            _logger.info('Ignoring the function %s without a connected database', fname)
            return

        arg_name = 'server_url'
        if arg_name in inspect.signature(function).parameters:
            _logger.debug('Adding server_url param to %s', fname)
            kwargs[arg_name] = server_url

        return function(*args, **kwargs)
    return wrapper


def save_conf_server(url, token, db_uuid, enterprise_code, db_name=None):
    """
    Save server configurations in odoo.conf
    :param url: The URL of the server
    :param token: The token to authenticate the server
    :param db_uuid: The database UUID
    :param enterprise_code: The enterprise code
    :param db_name: The database name
    """
    system.update_conf({
        'remote_server': url,
        'token': token,
        'db_uuid': db_uuid,
        'enterprise_code': enterprise_code,
        'db_name': db_name,
    })
    get_odoo_server_url.cache_clear()


@cache
def get_odoo_server_url():
    """Get the URL of the linked Odoo database.

    :return: The URL of the linked Odoo database.
    :rtype: str or None
    """
    return system.get_conf('remote_server')


def get_token():
    """:return: The token to authenticate the server"""
    return system.get_conf('token')


def delete_iot_handlers():
    """Delete all drivers, interfaces and libs if any.
    This is needed to avoid conflicts with the newly downloaded drivers.
    """
    try:
        iot_handlers = Path(file_path('iot_drivers/iot_handlers'))
        for file in iot_handlers.glob('**/*'):
            if file.is_file():
                file.unlink()
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
    etag = system.get_conf('iot_handlers_etag')
    try:
        response = requests.post(
            server_url + '/iot/get_handlers',
            data={'identifier': IOT_IDENTIFIER, 'auto': auto},
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
        system.update_conf({'iot_handlers_etag': response.headers['ETag'].strip('"')})
    except KeyError:
        _logger.exception('No ETag in the response headers')

    try:
        zip_file = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        _logger.exception('Bad IoT handlers response received: not a zip file')
        return

    delete_iot_handlers()
    path = system.path_file('odoo', 'addons', 'iot_drivers', 'iot_handlers')
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


def download_from_url(url, dest):
    """Download a file from a URL

    :param str url: The URL to download the file from
    :param PathLike dest: The path to the file where to save the downloaded file
    """
    try:
        request_response = requests.get(url, timeout=60)
        request_response.raise_for_status()
        dest.write_bytes(request_response.content)
        _logger.info('Downloaded %s from %s', dest, url)
    except requests.exceptions.RequestException:
        _logger.exception('Failed to download from %s', url)


def unzip_file(zipped, dest):
    """Unzip a file and delete the .zip file

    :param PathLike zipped: The path to the zip file
    :param PathLike dest: The path to the directory where to extract the zip file
    """
    try:
        with zipfile.ZipFile(zipped) as zip_file:
            zip_file.extractall(dest)
        zipped.unlink()
        _logger.info('Unzipped %s to %s', zipped, dest)
    except Exception:
        _logger.exception('Failed to unzip %s', zipped)


def disconnect_from_server():
    """Disconnect the IoT Box from the server"""
    system.update_conf({
        'remote_server': '',
        'token': '',
        'db_uuid': '',
        'db_name': '',
        'enterprise_code': '',
        'screen_orientation': '',
        'browser_url': '',
        'iot_handlers_etag': '',
    })
    odoo_restart()


def save_browser_state(url=None, orientation=None):
    """Save the browser state to the file

    :param url: The URL the browser is on (if None, the URL is not saved)
    :param orientation: The orientation of the screen (if None, the orientation is not saved)
    """
    to_update = {
        "browser_url": url,
        "screen_orientation": orientation.name.lower() if orientation else None,
    }
    # Only update the values that are not None
    system.update_conf({k: v for k, v in to_update.items() if v is not None})


def load_browser_state():
    """Load the browser state from the file

    :return: The URL the browser is on and the orientation of the screen (default to NORMAL)
    """
    url = system.get_conf('browser_url')
    orientation = system.get_conf('screen_orientation') or Orientation.NORMAL.name
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
    log_level_reset_timestamp = system.get_conf('log_level_reset_timestamp')
    if log_level_reset_timestamp and float(log_level_reset_timestamp) <= time.time():
        _logger.info("Resetting log level to default.")
        system.update_conf({
            'log_level_reset_timestamp': '',
            'log_handler': ':INFO,werkzeug:WARNING',
            'log_level': 'info',
        })


def check_network(host=None):
    host = host or system.get_gateway()
    if not host:
        return None

    host = socket.gethostbyname(host)
    packet_loss, avg_latency = system.mtr(host)
    thresholds = {"fast": 5, "normal": 20} if ip_address(host).is_private else {"fast": 50, "normal": 150}

    if packet_loss is None or packet_loss >= 50 or avg_latency is None:
        return "unreachable"
    if avg_latency < thresholds["fast"] and packet_loss < 1:
        return "fast"
    if avg_latency < thresholds["normal"] and packet_loss < 5:
        return "normal"
    return "slow"
