import datetime
import logging
import requests
from cryptography import x509
from cryptography.x509.oid import NameOID
from pathlib import Path

from odoo.addons.iot_drivers.tools.helpers import (
    get_conf,
    get_identifier,
    get_path_nginx,
    get_version,
    odoo_restart,
    require_db,
    start_nginx_server,
    update_conf,
)
from odoo.addons.iot_drivers.tools.system import IS_RPI, IS_TEST, IS_WINDOWS

_logger = logging.getLogger(__name__)


@require_db
def ensure_validity():
    """Ensure that the certificate is up to date
    Load a new if the current one is not valid or if there is none.

    This method also sends the certificate end date to the database.
    """
    inform_database(get_certificate_end_date() or download_odoo_certificate())


def get_certificate_end_date():
    """Check if the certificate is up to date and valid

    :return: End date of the certificate if it is valid, None otherwise
    :rtype: str
    """
    base_path = [get_path_nginx(), 'conf'] if IS_WINDOWS else ['/etc/ssl/certs']
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

    # Ensure cryptography compatibility with python < 3.13
    if IS_RPI and float(get_version()[1:8]) < 2025.10:
        cert_end_date = cert.not_valid_after
        now = datetime.datetime.now()
    else:
        cert_end_date = cert.not_valid_after_utc
        now = datetime.datetime.now(datetime.timezone.utc)
    if (
        common_name == 'OdooTempIoTBoxCertificate'
        or now > cert_end_date - datetime.timedelta(days=10)
    ):
        _logger.debug("SSL certificate '%s' must be updated.", common_name)
        return None

    _logger.debug("SSL certificate '%s' is valid until %s", common_name, cert_end_date)
    return str(cert_end_date)


def download_odoo_certificate(retry=0):
    """Send a request to Odoo with customer db_uuid and enterprise_code
    to get a true certificate
    """
    if IS_TEST:
        _logger.info("Skipping certificate download in test mode.")
        return None
    db_uuid = get_conf('db_uuid')
    enterprise_code = get_conf('enterprise_code')
    if not db_uuid:
        return None
    try:
        response = requests.post(
            'https://www.odoo.com/odoo-enterprise/iot/x509',
            json={'params': {'db_uuid': db_uuid, 'enterprise_code': enterprise_code}},
            timeout=95,  # let's encrypt library timeout
        )
        response.raise_for_status()
        response_body = response.json()
    except (requests.exceptions.RequestException, ValueError) as e:
        _logger.warning("An error occurred while trying to reach odoo.com to get a new certificate: %s", e)
        if retry < 5:
            return download_odoo_certificate(retry=retry + 1)
        return _logger.exception("Maximum attempt to download the odoo.com certificate reached")

    server_error = response_body.get('error')
    if server_error:
        _logger.error("Server error received from odoo.com while trying to get the certificate: %s", server_error)
        return None

    result = response_body.get('result', {})
    certificate_error = result.get('error')
    if certificate_error:
        _logger.warning("Error received from odoo.com while trying to get the certificate: %s", certificate_error)
        return None

    update_conf({'subject': result['subject_cn']})

    certificate = result['x509_pem']
    private_key = result['private_key_pem']
    if not certificate or not private_key:  # ensure not empty strings
        _logger.error("The certificate received from odoo.com is not valid.")
        return None

    if IS_RPI:
        Path('/etc/ssl/certs/nginx-cert.crt').write_text(certificate, encoding='utf-8')
        Path('/root_bypass_ramdisks/etc/ssl/certs/nginx-cert.crt').write_text(certificate, encoding='utf-8')
        Path('/etc/ssl/private/nginx-cert.key').write_text(private_key, encoding='utf-8')
        Path('/root_bypass_ramdisks/etc/ssl/private/nginx-cert.key').write_text(private_key, encoding='utf-8')
        start_nginx_server()
        cert = x509.load_pem_x509_certificate(certificate.encode())
        if float(get_version()[1:8]) < 2025.10:
            return str(cert.not_valid_after)
        else:
            return str(cert.not_valid_after_utc)
    else:
        Path(get_path_nginx(), 'conf', 'nginx-cert.crt').write_text(certificate, encoding='utf-8')
        Path(get_path_nginx(), 'conf', 'nginx-cert.key').write_text(private_key, encoding='utf-8')
        odoo_restart(3)
        return None


@require_db
def inform_database(ssl_certificate_end_date, server_url=None):
    """Inform the database about the certificate end date.

    If end date is ``None``, we avoid sending a useless request.

    :param str ssl_certificate_end_date: End date of the SSL certificate
    :param str server_url: URL of the Odoo server (provided by decorator).
    """
    if not ssl_certificate_end_date:
        return

    try:
        response = requests.post(
            server_url + "/iot/box/update_certificate_status",
            json={'params': {'identifier': get_identifier(), 'ssl_certificate_end_date': ssl_certificate_end_date}},
            timeout=5,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException:
        _logger.exception("Could not reach configured server to inform about the certificate status")
