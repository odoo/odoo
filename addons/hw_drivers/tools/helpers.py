# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import netifaces
from pathlib import Path
import datetime
from OpenSSL import crypto
import urllib3
import json
import logging
import subprocess

from odoo import _

_logger = logging.getLogger(__name__)

#----------------------------------------------------------
# Helper
#----------------------------------------------------------

def access_point():
    return get_ip() == '10.11.12.1'

def add_credential(db_uuid, enterprise_code):
    write_file('odoo-db-uuid.conf', db_uuid)
    write_file('odoo-enterprise-code.conf', enterprise_code)

def check_certificate():
    """
    Check if the current certificate is up to date or not authenticated
    """
    server = get_odoo_server_url()
    if server:
        path = Path('/etc/ssl/certs/nginx-cert.crt')
        if path.exists():
            with path.open('r') as f:
                cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
                cert_end_date = datetime.datetime.strptime(cert.get_notAfter().decode('utf-8'), "%Y%m%d%H%M%SZ") - datetime.timedelta(days=10)
                for key in cert.get_subject().get_components():
                    if key[0] == b'CN':
                        cn = key[1].decode('utf-8')
                if cn == 'OdooTempIoTBoxCertificate' or datetime.datetime.now() > cert_end_date:
                    _logger.info(_('Your certificate %s must be updated') % (cn))
                    load_certificate()
                else:
                    _logger.info(_('Your certificate %s is valid until %s') % (cn, cert_end_date))
        else:
            load_certificate()

def get_ip():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_INET][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_INET][0]['addr']

def get_mac_address():
    try:
        return netifaces.ifaddresses('eth0')[netifaces.AF_LINK][0]['addr']
    except:
        return netifaces.ifaddresses('wlan0')[netifaces.AF_LINK][0]['addr']

def get_odoo_server_url():
    return read_file_first_line('odoo-remote-server.conf')

def get_token():
    return read_file_first_line('token')

def get_version():
    return '19_07'

def load_certificate():
    """
    Send a request to Odoo with customer db_uuid and enterprise_code to get a true certificate
    """
    db_uuid = read_file_first_line('odoo-db-uuid.conf')
    enterprise_code = read_file_first_line('odoo-enterprise-code.conf')
    if db_uuid and enterprise_code:
        url = 'https://www.odoo.com/odoo-enterprise/iot/x509'
        data = {
            'params': {
                'db_uuid': db_uuid,
                'enterprise_code': enterprise_code
            }
        }
        urllib3.disable_warnings()
        http = urllib3.PoolManager(cert_reqs='CERT_NONE')
        response = http.request(
            'POST',
            url,
            body = json.dumps(data).encode('utf8'),
            headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        )
        result = json.loads(response.data.decode('utf8'))['result']
        if result:
            write_file('odoo-subject.conf', result['subject_cn'])
            subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
            subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/root_bypass_ramdisks/"])
            Path('/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'])
            Path('/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
            Path('/root_bypass_ramdisks/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'])
            subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
            subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/root_bypass_ramdisks/"])
            subprocess.check_call(["sudo", "service", "nginx", "restart"])

def read_file_first_line(filename):
    path = Path.home() / filename
    path = Path('/home/pi/' + filename)
    if path.exists():
        with path.open('r') as f:
            return f.readline().strip('\n')
    return ''

def unlink_file(filename):
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
    path = Path.home() / filename
    if path.exists():
        path.unlink()
    subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])

def write_file(filename, text):
    subprocess.check_call(["sudo", "mount", "-o", "remount,rw", "/"])
    path = Path.home() / filename
    path.write_text(text)
    subprocess.check_call(["sudo", "mount", "-o", "remount,ro", "/"])
