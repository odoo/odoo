# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import configparser
import contextlib
import datetime
from enum import Enum
from functools import cache
from importlib import util
import io
import logging
import netifaces
from OpenSSL import crypto
import os
from pathlib import Path
import platform
import requests
import secrets
import socket
import subprocess
from urllib.parse import parse_qs
import urllib3.util
from threading import Thread, Lock
import time
import zipfile

from odoo import http, release, service
from odoo.tools.func import lazy_property
from odoo.tools.misc import file_path

lock = Lock()
_logger = logging.getLogger(__name__)

try:
    import crypt
except ImportError:
    _logger.warning('Could not import library crypt')


class Orientation(Enum):
    """xrandr screen orientation for kiosk mode"""
    NORMAL = 'normal'
    INVERTED = 'inverted'
    LEFT = 'left'
    RIGHT = 'right'


class CertificateStatus(Enum):
    OK = 1
    NEED_REFRESH = 2
    ERROR = 3


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


if platform.system() == 'Windows':
    writable = contextlib.nullcontext
elif platform.system() == 'Linux':
    @contextlib.contextmanager
    def writable():
        with lock:
            try:
                subprocess.run(["sudo", "mount", "-o", "remount,rw", "/"], check=False)
                subprocess.run(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/"], check=False)
                yield
            finally:
                subprocess.run(["sudo", "mount", "-o", "remount,ro", "/"], check=False)
                subprocess.run(["sudo", "mount", "-o", "remount,ro", "/root_bypass_ramdisks/"], check=False)
                subprocess.run(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"], check=False)


def start_nginx_server():
    if platform.system() == 'Windows':
        path_nginx = get_path_nginx()
        if path_nginx:
            os.chdir(path_nginx)
            _logger.info('Start Nginx server: %s\\nginx.exe', path_nginx)
            os.popen('nginx.exe')
            os.chdir('..\\server')
    elif platform.system() == 'Linux':
        subprocess.check_call(["sudo", "service", "nginx", "restart"])

def check_certificate():
    """
    Check if the current certificate is up to date or not authenticated
    :return CheckCertificateStatus
    """
    server = get_odoo_server_url()

    if not server:
        _logger.info('Ignoring the nginx certificate check without a connected database')
        return {"status": CertificateStatus.ERROR,
                "error_code": "ERR_IOT_HTTPS_CHECK_NO_SERVER"}

    if platform.system() == 'Windows':
        path = Path(get_path_nginx()).joinpath('conf/nginx-cert.crt')
    elif platform.system() == 'Linux':
        path = Path('/etc/ssl/certs/nginx-cert.crt')

    if not path.exists():
        return {"status": CertificateStatus.NEED_REFRESH}

    try:
        with path.open('r') as f:
            cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    except EnvironmentError:
        _logger.exception("Unable to read certificate file")
        return {"status": CertificateStatus.ERROR,
                "error_code": "ERR_IOT_HTTPS_CHECK_CERT_READ_EXCEPTION"}

    cert_end_date = datetime.datetime.strptime(cert.get_notAfter().decode('utf-8'), "%Y%m%d%H%M%SZ") - datetime.timedelta(days=10)
    for key in cert.get_subject().get_components():
        if key[0] == b'CN':
            cn = key[1].decode('utf-8')
    if cn == 'OdooTempIoTBoxCertificate' or datetime.datetime.now() > cert_end_date:
        message = 'Your certificate %s must be updated' % cn
        _logger.info(message)
        return {"status": CertificateStatus.NEED_REFRESH}
    else:
        message = 'Your certificate %(certificate)s is valid until %(end_date)s' % {"certificate": cn, "end_date": cert_end_date}
        _logger.info(message)
        return {"status": CertificateStatus.OK, "message": message}


def check_git_branch():
    """Check if the local branch is the same as the connected Odoo DB and
    checkout to match it if needed.
    """
    try:
        response = requests.post(get_odoo_server_url() + "/web/webclient/version_info", json={}, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError:
        _logger.exception('Could not reach configured server to get the Odoo version')
        return
    except ValueError:
        _logger.exception('Could not load JSON data: Received data is not valid JSON.\nContent:\n%s', response.content)
        return

    try:
        git = ['git', '--work-tree=/home/pi/odoo/', '--git-dir=/home/pi/odoo/.git']

        db_branch = data['result']['server_serie'].replace('~', '-')
        if not subprocess.check_output(git + ['ls-remote', 'origin', db_branch]):
            db_branch = 'master'

        local_branch = (
            subprocess.check_output(git + ['symbolic-ref', '-q', '--short', 'HEAD']).decode('utf-8').rstrip()
        )
        _logger.info(
            "Current IoT Box local git branch: %s / Associated Odoo database's git branch: %s",
            local_branch,
            db_branch,
        )

        if db_branch != local_branch:
            try:
                with writable():
                    subprocess.run(git + ['branch', '-m', db_branch], check=True)
                    subprocess.run(git + ['remote', 'set-branches', 'origin', db_branch], check=True)
                    _logger.info("Updating odoo folder to the branch %s", db_branch)
                    subprocess.run(
                        ['/home/pi/odoo/addons/iot_box_image/configuration/checkout.sh'], check=True
                    )
            except subprocess.CalledProcessError:
                _logger.exception("Failed to update the code with git.")
            finally:
                odoo_restart()
    except Exception:
        _logger.exception('An error occurred while trying to update the code with git')


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
    if value_actual == value_latest:
        return False
    version = check_file.get(value_latest, 'Error').replace('iotboxv', '').replace('.zip', '').split('_')
    return {'major': version[0], 'minor': version[1]}


def save_conf_server(url, token, db_uuid, enterprise_code):
    """
    Save server configurations in odoo.conf
    :param url: The URL of the server
    :param token: The token to authenticate the server
    :param db_uuid: The database UUID
    :param enterprise_code: The enterprise code
    """
    update_conf({
        'remote_server': url,
        'token': token,
        'db_uuid': db_uuid,
        'enterprise_code': enterprise_code,
    })


def generate_password():
    """
    Generate an unique code to secure raspberry pi
    """
    alphabet = 'abcdefghijkmnpqrstuvwxyz23456789'
    password = ''.join(secrets.choice(alphabet) for i in range(12))
    try:
        shadow_password = crypt.crypt(password, crypt.mksalt())
        subprocess.run(('sudo', 'usermod', '-p', shadow_password, 'pi'), check=True)
        with writable():
            subprocess.run(('sudo', 'cp', '/etc/shadow', '/root_bypass_ramdisks/etc/shadow'), check=True)
        return password
    except subprocess.CalledProcessError as e:
        _logger.exception("Failed to generate password: %s", e.output)
        return 'Error: Check IoT log'


def get_certificate_status(is_first=True):
    """
    Will get the HTTPS certificate details if present. Will load the certificate if missing.

    :param is_first: Use to make sure that the recursion happens only once
    :return: (bool, str)
    """
    check_certificate_result = check_certificate()
    certificateStatus = check_certificate_result["status"]

    if certificateStatus == CertificateStatus.ERROR:
        return False, check_certificate_result["error_code"]

    if certificateStatus == CertificateStatus.NEED_REFRESH and is_first:
        certificate_process = load_certificate()
        if certificate_process is not True:
            return False, certificate_process
        return get_certificate_status(is_first=False)  # recursive call to attempt certificate read
    return True, check_certificate_result.get("message",
                                              "The HTTPS certificate was generated correctly")

def get_img_name():
    major, minor = get_version()[1:].split('.')
    return 'iotboxv%s_%s.zip' % (major, minor)

def get_ip():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if netifaces.ifaddresses(interface).get(netifaces.AF_INET):
            addr = netifaces.ifaddresses(interface).get(netifaces.AF_INET)[0]['addr']
            if addr != '127.0.0.1':
                return addr

def get_mac_address():
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if netifaces.ifaddresses(interface).get(netifaces.AF_INET):
            addr = netifaces.ifaddresses(interface).get(netifaces.AF_LINK)[0]['addr']
            if addr != '00:00:00:00:00:00':
                return addr

def get_path_nginx():
    return str(list(Path().absolute().parent.glob('*nginx*'))[0])


@cache
def get_odoo_server_url():
    """Get the URL of the linked Odoo database.
    If no internet connection is available, return None to avoid trying
    to reach the server.

    :return: The URL of the linked Odoo database.
    :rtype: str or None
    """
    if get_ip() == "10.11.12.1":
        return None
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
    if platform.system() == 'Linux':
        image_version = read_file_first_line('/var/odoo/iotbox_version')
    elif platform.system() == 'Windows':
        # updated manually when big changes are made to the windows virtual IoT
        image_version = '23.11'

    version = platform.system()[0] + image_version
    if detailed_version:
        # Note: on windows IoT, the `release.version` finish with the build date
        version += f"-{release.version}"
        if platform.system() == 'Linux':
            version += f'#{get_commit_hash()}'

    return version


def load_certificate():
    """
    Send a request to Odoo with customer db_uuid and enterprise_code to get a true certificate
    """
    db_uuid = get_conf('db_uuid')
    enterprise_code = get_conf('enterprise_code')
    if not (db_uuid and enterprise_code):
        return "ERR_IOT_HTTPS_LOAD_NO_CREDENTIAL"

    try:
        response = requests.post(
            'https://www.odoo.com/odoo-enterprise/iot/x509',
            json = {'params': {'db_uuid': db_uuid, 'enterprise_code': enterprise_code}},
            timeout=5,
        )
        response.raise_for_status()
        result = response.json()['result']
    except requests.exceptions.RequestException as e:
        _logger.exception("An error occurred while trying to reach odoo.com servers.")
        return "ERR_IOT_HTTPS_LOAD_REQUEST_EXCEPTION\n\n%s" % e
    except ValueError:
        return "ERR_IOT_HTTPS_LOAD_REQUEST_NO_RESULT"

    update_conf({'subject': result['subject_cn']})
    if platform.system() == 'Linux':
        with writable():
            Path('/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
    elif platform.system() == 'Windows':
        Path(get_path_nginx()).joinpath('conf/nginx-cert.crt').write_text(result['x509_pem'])
        Path(get_path_nginx()).joinpath('conf/nginx-cert.key').write_text(result['private_key_pem'])
    time.sleep(3)
    if platform.system() == 'Windows':
        odoo_restart(0)
    elif platform.system() == 'Linux':
        start_nginx_server()
    return True


def delete_iot_handlers():
    """
    Delete all the drivers and interfaces
    This is needed to avoid conflicts
    with the newly downloaded drivers
    """
    try:
        for directory in ['drivers', 'interfaces', 'lib']:
            iot_handlers = file_path(f'hw_drivers/iot_handlers/{directory}')
            for file in Path(iot_handlers).iterdir():
                if file.is_file():
                    unlink_file(f"odoo/addons/hw_drivers/iot_handlers/{directory}/{file.name}")
        _logger.info("Deleted old IoT handlers")
    except OSError:
        _logger.exception('Failed to delete old IoT handlers')


def download_iot_handlers(auto=True):
    """
    Get the drivers from the configured Odoo server
    """
    server = get_odoo_server_url()
    if server:
        try:
            response = requests.post(
                server + '/iot/get_handlers', data={'mac': get_mac_address(), 'auto': auto}, timeout=8
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.exception('Could not reach configured server to download IoT handlers')
            return

        data = response.content
        if not data:
            return

        delete_iot_handlers()
        with writable():
            path = path_file('odoo', 'addons', 'hw_drivers', 'iot_handlers')
            zip_file = zipfile.ZipFile(io.BytesIO(data))
            zip_file.extractall(path)


def compute_iot_handlers_addon_name(handler_kind, handler_file_name):
    return "odoo.addons.hw_drivers.iot_handlers.{handler_kind}.{handler_name}".\
        format(handler_kind=handler_kind, handler_name=handler_file_name.removesuffix('.py'))

def load_iot_handlers():
    """
    This method loads local files: 'odoo/addons/hw_drivers/iot_handlers/drivers' and
    'odoo/addons/hw_drivers/iot_handlers/interfaces'
    And execute these python drivers and interfaces
    """
    for directory in ['interfaces', 'drivers']:
        path = file_path(f'hw_drivers/iot_handlers/{directory}')
        filesList = list_file_by_os(path)
        for file in filesList:
            spec = util.spec_from_file_location(compute_iot_handlers_addon_name(directory, file), str(Path(path).joinpath(file)))
            if spec:
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except Exception:
                    _logger.exception('Unable to load handler file: %s', file)
    lazy_property.reset_all(http.root)

def list_file_by_os(file_list):
    platform_os = platform.system()
    if platform_os == 'Linux':
        return [x.name for x in Path(file_list).glob('*[!W].*')]
    elif platform_os == 'Windows':
        return [x.name for x in Path(file_list).glob('*[!L].*')]


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
    platform_os = platform.system()
    if platform_os == 'Linux':
        return Path("~pi", *args).expanduser()  # Path.home() returns odoo user's home instead of pi's
    elif platform_os == 'Windows':
        return Path().absolute().parent.joinpath('server', *args)


def read_file_first_line(filename):
    path = path_file(filename)
    if path.exists():
        with path.open('r') as f:
            return f.readline().strip('\n')


def unlink_file(filename):
    with writable():
        path = path_file(filename)
        if path.exists():
            path.unlink()


def write_file(filename, text, mode='w'):
    """This function writes 'text' to 'filename' file

    :param filename: The name of the file to write to
    :param text: The text to write to the file
    :param mode: The mode to open the file in (Default: 'w')
    """
    with writable():
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
        with writable():
            path = path_file(path_to_filename)
            with zipfile.ZipFile(path) as zip_file:
                zip_file.extractall(path_file(path_to_extract))
            Path(path).unlink()
        _logger.info('Unzipped %s to %s', path_to_filename, path_to_extract)
    except Exception:
        _logger.exception('Failed to unzip %s', path_to_filename)


@cache
def get_hostname():
    """Cache the hostname to avoid multiple calls to socket.gethostname()"""
    return socket.gethostname()


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

    with writable():
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
    """Disconnect the IoT Box from the server, clears associated caches"""
    get_odoo_server_url.cache_clear()
    update_conf({
        'remote_server': '',
        'token': '',
        'db_uuid': '',
        'enterprise_code': '',
    })


def save_browser_state(url=None, orientation=None):
    """Save the browser state to the file

    :param url: The URL the browser is on (if None, the URL is not saved)
    :param orientation: The orientation of the screen (if None, the orientation is not saved)
    """
    update_conf({
        'browser_url': url,
        'screen_orientation': orientation.value if orientation else None,
    })


def load_browser_state():
    """Load the browser state from the file

    :return: The URL the browser is on and the orientation of the screen (default to NORMAL)
    """
    url = get_conf('browser_url')
    orientation = get_conf('screen_orientation') or Orientation.NORMAL
    return url, Orientation(orientation)


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
    This timestamp is set by the log controller in `hw_posbox_homepage/homepage.py` when the log level is changed
    """
    log_level_reset_timestamp = get_conf('log_level_reset_timestamp')
    if log_level_reset_timestamp and float(log_level_reset_timestamp) <= time.time():
        _logger.info("Resetting log level to default.")
        update_conf({
            'log_level_reset_timestamp': '',
            'log_handler': ':WARNING',
            'log_level': 'warn',
        })
