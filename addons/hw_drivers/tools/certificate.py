import datetime
import logging
import platform
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from pathlib import Path

from odoo.addons.hw_drivers.tools.helpers import (
    require_db,
    get_conf,
    update_conf,
    get_path_nginx,
    writable,
    start_nginx_server,
    odoo_restart,
)

_logger = logging.getLogger(__name__)


@require_db
def ensure_validity():
    """Ensure that the certificate is up to date
    Load a new if the current one is not valid or if there is none.
    """
    get_certificate_end_date() or download_odoo_certificate()


def get_certificate_end_date():
    """Check if the certificate is up to date and valid

    :return: End date of the certificate if it is valid, None otherwise
    :rtype: str
    """
    base_path = [get_path_nginx(), 'conf'] if platform.system() == 'Windows' else ['/etc/ssl/certs']
    path = Path(*base_path, 'nginx-cert.crt')
    if not path.exists():
        return None

    try:
        cert = x509.load_pem_x509_certificate(path.read_bytes())
    except ValueError:
        _logger.exception("Unable to read certificate file.")
        return None

    common_name = next(
        (name_attribute.value for name_attribute in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)), ''
    )

    cert_end_date = cert.not_valid_after
    if (
        common_name == 'OdooTempIoTBoxCertificate'
        or datetime.datetime.now() > cert_end_date - datetime.timedelta(days=10)
    ):
        _logger.info("SSL certificate '%s' must be updated.", common_name)
        return None

    _logger.info("SSL certificate '%s' is valid until %s", common_name, cert_end_date)
    return str(cert_end_date)


def download_odoo_certificate():
    """Send a request to Odoo with customer db_uuid and enterprise_code
    to get a true certificate
    """
    db_uuid = get_conf('db_uuid')
    enterprise_code = get_conf('enterprise_code')
    if not db_uuid:
        return False

    try:
        response = requests.post(
            'https://www.odoo.com/odoo-enterprise/iot/x509',
            json={'params': {'db_uuid': db_uuid, 'enterprise_code': enterprise_code}},
            timeout=5,
        )
        response.raise_for_status()
        result = response.json().get('result', {})
    except (requests.exceptions.RequestException, ValueError):
        _logger.exception("An error occurred while trying to reach odoo.com")
        return False

    error = result.get('error')
    if error:
        _logger.warning("Error received from odoo.com while trying to get the certificate: %s", error)
        return False

    update_conf({'subject': result['subject_cn']})
    if platform.system() == 'Linux':
        with writable():
            Path('/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'], encoding='utf-8')
            Path('/root_bypass_ramdisks/etc/ssl/certs/nginx-cert.crt').write_text(result['x509_pem'], encoding='utf-8')
            Path('/etc/ssl/private/nginx-cert.key').write_text(result['private_key_pem'], encoding='utf-8')
            Path('/root_bypass_ramdisks/etc/ssl/private/nginx-cert.key').write_text(
                result['private_key_pem'], encoding='utf-8'
            )
        start_nginx_server()
    else:
        Path(get_path_nginx(), 'conf', 'nginx-cert.crt').write_text(result['x509_pem'], encoding='utf-8')
        Path(get_path_nginx(), 'conf', 'nginx-cert.key').write_text(result['private_key_pem'], encoding='utf-8')
        odoo_restart(3)
    return True
