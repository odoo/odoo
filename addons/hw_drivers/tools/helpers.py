# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from enum import Enum
from importlib import util
import platform
import io
import json
import logging
import netifaces
from OpenSSL import crypto
import os
from pathlib import Path
import subprocess
import urllib3
import zipfile
from threading import Thread
import time
import contextlib
import requests

from odoo import _, http, service
from odoo.tools.func import lazy_property
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Helper
#----------------------------------------------------------


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
        subprocess.call(["sudo", "mount", "-o", "remount,rw", "/"])
        subprocess.call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/"])
        try:
            yield
        finally:
            subprocess.call(["sudo", "mount", "-o", "remount,ro", "/"])
            subprocess.call(["sudo", "mount", "-o", "remount,ro", "/root_bypass_ramdisks/"])
            subprocess.call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/etc/cups"])

def access_point():
    return get_ip() == '10.11.12.1'

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
        message = _('Your certificate %s must be updated') % (cn)
        _logger.info(message)
        return {"status": CertificateStatus.NEED_REFRESH}
    else:
        message = _('Your certificate %s is valid until %s') % (cn, cert_end_date)
        _logger.info(message)
        return {"status": CertificateStatus.OK, "message": message}

def check_git_branch():
    """
    Check if the local branch is the same than the connected Odoo DB and
    checkout to match it if needed.
    """
    server = get_odoo_server_url()
    if server:
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        try:
            response = http.request(
                'POST',
                server + "/web/webclient/version_info",
                body = '{}',
                headers = {'Content-type': 'application/json'}
            )

            if response.status == 200:
                git = ['git', '--work-tree=/home/pi/odoo/', '--git-dir=/home/pi/odoo/.git']

                db_branch = json.loads(response.data)['result']['server_serie'].replace('~', '-')
                if not subprocess.check_output(git + ['ls-remote', 'origin', db_branch]):
                    db_branch = 'master'

                local_branch = subprocess.check_output(git + ['symbolic-ref', '-q', '--short', 'HEAD']).decode('utf-8').rstrip()

                if db_branch != local_branch:
                    with writable():
                        subprocess.check_call(["rm", "-rf", "/home/pi/odoo/addons/hw_drivers/iot_handlers/drivers/*"])
                        subprocess.check_call(["rm", "-rf", "/home/pi/odoo/addons/hw_drivers/iot_handlers/interfaces/*"])
                        subprocess.check_call(git + ['branch', '-m', db_branch])
                        subprocess.check_call(git + ['remote', 'set-branches', 'origin', db_branch])
                        os.system('/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/posbox_update.sh')

        except Exception as e:
            _logger.error('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)

def check_image():
    """
    Check if the current image of IoT Box is up to date
    """
    url = 'https://nightly.odoo.com/master/iotbox/SHA1SUMS.txt'
    urllib3.disable_warnings()
    http = urllib3.PoolManager(cert_reqs='CERT_NONE')
    response = http.request('GET', url)
    checkFile = {}
    valueActual = ''
    for line in response.data.decode().split('\n'):
        if line:
            value, name = line.split('  ')
            checkFile.update({value: name})
            if name == 'iotbox-latest.zip':
                valueLastest = value
            elif name == get_img_name():
                valueActual = value
    if valueActual == valueLastest:
        return False
    version = checkFile.get(valueLastest, 'Error').replace('iotboxv', '').replace('.zip', '').split('_')
    return {'major': version[0], 'minor': version[1]}

def save_conf_server(url, token, db_uuid, enterprise_code):
    """
    Save config to connect IoT to the server
    """
    write_file('odoo-remote-server.conf', url)
    write_file('token', token)
    write_file('odoo-db-uuid.conf', db_uuid or '')
    write_file('odoo-enterprise-code.conf', enterprise_code or '')

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
    major, minor = get_version().split('.')
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

def get_ssid():
    ap = subprocess.call(['systemctl', 'is-active', '--quiet', 'hostapd']) # if service is active return 0 else inactive
    if not ap:
        return subprocess.check_output(['grep', '-oP', '(?<=ssid=).*', '/etc/hostapd/hostapd.conf']).decode('utf-8').rstrip()
    process_iwconfig = subprocess.Popen(['iwconfig'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_grep = subprocess.Popen(['grep', 'ESSID:"'], stdin=process_iwconfig.stdout, stdout=subprocess.PIPE)
    return subprocess.check_output(['sed', 's/.*"\\(.*\\)"/\\1/'], stdin=process_grep.stdout).decode('utf-8').rstrip()

def get_odoo_server_url():
    if platform.system() == 'Linux':
        ap = subprocess.call(['systemctl', 'is-active', '--quiet', 'hostapd']) # if service is active return 0 else inactive
        if not ap:
            return False
    return read_file_first_line('odoo-remote-server.conf')

def get_token():
    return read_file_first_line('token')

def get_version():
    if platform.system() == 'Linux':
        return read_file_first_line('/var/odoo/iotbox_version')
    elif platform.system() == 'Windows':
        return 'W22_11'

def get_wifi_essid():
    wifi_options = []
    process_iwlist = subprocess.Popen(['sudo', 'iwlist', 'wlan0', 'scan'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process_grep = subprocess.Popen(['grep', 'ESSID:"'], stdin=process_iwlist.stdout, stdout=subprocess.PIPE).stdout.readlines()
    for ssid in process_grep:
        essid = ssid.decode('utf-8').split('"')[1]
        if essid not in wifi_options:
            wifi_options.append(essid)
    return wifi_options

def load_certificate():
    """
    Send a request to Odoo with customer db_uuid and enterprise_code to get a true certificate
    """
    db_uuid = read_file_first_line('odoo-db-uuid.conf')
    enterprise_code = read_file_first_line('odoo-enterprise-code.conf')
    if not (db_uuid and enterprise_code):
        return "ERR_IOT_HTTPS_LOAD_NO_CREDENTIAL"

    url = 'https://www.odoo.com/odoo-enterprise/iot/x509'
    data = {
        'params': {
            'db_uuid': db_uuid,
            'enterprise_code': enterprise_code
        }
    }
    urllib3.disable_warnings()
    http = urllib3.PoolManager(cert_reqs='CERT_NONE', retries=urllib3.Retry(4))
    try:
        response = http.request(
            'POST',
            url,
            body = json.dumps(data).encode('utf8'),
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        )
    except Exception as e:
        _logger.exception("An error occurred while trying to reach odoo.com servers.")
        return "ERR_IOT_HTTPS_LOAD_REQUEST_EXCEPTION\n\n%s" % e

    if response.status != 200:
        return "ERR_IOT_HTTPS_LOAD_REQUEST_STATUS %s\n\n%s" % (response.status, response.reason)

    result = json.loads(response.data.decode('utf8'))['result']
    if not result:
        return "ERR_IOT_HTTPS_LOAD_REQUEST_NO_RESULT"

    write_file('odoo-subject.conf', result['subject_cn'])
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

def download_iot_handlers(auto=True):
    """
    Get the drivers from the configured Odoo server
    """
    server = get_odoo_server_url()
    if server:
        urllib3.disable_warnings()
        pm = urllib3.PoolManager(cert_reqs='CERT_NONE')
        server = server + '/iot/get_handlers'
        try:
            resp = pm.request('POST', server, fields={'mac': get_mac_address(), 'auto': auto}, timeout=8)
            if resp.data:
                with writable():
                    drivers_path = ['odoo', 'addons', 'hw_drivers', 'iot_handlers']
                    path = path_file(str(Path().joinpath(*drivers_path)))
                    zip_file = zipfile.ZipFile(io.BytesIO(resp.data))
                    zip_file.extractall(path)
        except Exception as e:
            _logger.error('Could not reach configured server')
            _logger.error('A error encountered : %s ' % e)

def load_iot_handlers():
    """
    This method loads local files: 'odoo/addons/hw_drivers/iot_handlers/drivers' and
    'odoo/addons/hw_drivers/iot_handlers/interfaces'
    And execute these python drivers and interfaces
    """
    for directory in ['interfaces', 'drivers']:
        path = get_resource_path('hw_drivers', 'iot_handlers', directory)
        filesList = list_file_by_os(path)
        for file in filesList:
            spec = util.spec_from_file_location(file, str(Path(path).joinpath(file)))
            if spec:
                module = util.module_from_spec(spec)
                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    _logger.error('Unable to load file: %s ', file)
                    _logger.error('An error encountered : %s ', e)
    lazy_property.reset_all(http.root)

def list_file_by_os(file_list):
    platform_os = platform.system()
    if platform_os == 'Linux':
        return [x.name for x in Path(file_list).glob('*[!W].*')]
    elif platform_os == 'Windows':
        return [x.name for x in Path(file_list).glob('*[!L].*')]

def odoo_restart(delay):
    IR = IoTRestart(delay)
    IR.start()

def path_file(filename):
    platform_os = platform.system()
    if platform_os == 'Linux':
        return Path.home() / filename
    elif platform_os == 'Windows':
        return Path().absolute().parent.joinpath('server/' + filename)

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
    except Exception as e:
        _logger.error('Failed to download from %s: %s', download_url, e)

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
    except Exception as e:
        _logger.error('Failed to unzip %s: %s', path_to_filename, e)
