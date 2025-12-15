# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
import logging
import PyKCS11

from passlib.context import CryptContext

from odoo import http
from odoo.tools.config import config
from odoo.addons.iot_drivers.tools import route
from odoo.addons.iot_drivers.tools.system import IOT_SYSTEM, IS_RPI, IS_WINDOWS

_logger = logging.getLogger(__name__)

crypt_context = CryptContext(schemes=['pbkdf2_sha512'])


def _is_access_token_valid(access_token):
    stored_hash = config.get('proxy_access_token')
    if not stored_hash:
        # empty password/hash => authentication forbidden
        return False
    return crypt_context.verify(access_token, stored_hash)


def get_crypto_lib():
    """Get the path to the PKCS11 library depending on the system."""
    if IOT_SYSTEM == 'Darwin':
        return '/Library/OpenSC/lib/onepin-opensc-pkcs11.so', False
    elif IS_RPI:
        return '/usr/lib/x86_64-linux-gnu/opensc-pkcs11.so', False
    elif IS_WINDOWS:
        return 'C:/Windows/System32/eps2003csp11.dll', False

    return False, _get_error_template('unsupported_system')


def _get_session(pin):
    """Get a PKCS11 session with the given pin.

    :param pin: pin of the token
    :return: tuple of (session, error)
    """
    lib, error = get_crypto_lib()
    if error:
        return False, error

    try:
        pkcs11 = PyKCS11.PyKCS11Lib()
        pkcs11.load(pkcs11dll_filename=lib)
    except PyKCS11.PyKCS11Error:
        return False, _get_error_template('missing_dll')

    slots = pkcs11.getSlotList(tokenPresent=True)
    if not slots:
        return False, _get_error_template('no_drive')
    if len(slots) > 1:
        return False, _get_error_template('multiple_drive')

    try:
        session = pkcs11.openSession(slots[0], PyKCS11.CKF_SERIAL_SESSION | PyKCS11.CKF_RW_SESSION)
        session.login(pin)
        return session, False
    except Exception as ex:  # noqa: BLE001
        error = _get_error_template(str(ex))
    return False, error


def _get_error_template(error_str):
    return json.dumps({'error': error_str})


class EtaUsbController(http.Controller):
    @route.iot_route('/hw_l10n_eg_eta/certificate', type='http', cors='*', csrf=False, methods=['POST'])
    def eta_certificate(self, pin, access_token):
        """Gets the certificate from the token and returns it to the main odoo instance so that we can prepare the
        cades-bes object on the main odoo instance rather than this middleware

        :param pin: pin of the token
        :param access_token: token shared with the main odoo instance
        :return: json object with the certificate
        """
        if not _is_access_token_valid(access_token):
            return _get_error_template('unauthorized')
        session, error = _get_session(pin)
        if error:
            return error
        try:
            cert = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])[0]
            cert_bytes = bytes(session.getAttributeValue(cert, [PyKCS11.CKA_VALUE])[0])
            payload = {
                'certificate': base64.b64encode(cert_bytes).decode()
            }
            return json.dumps(payload)
        except Exception as ex:
            _logger.exception('Error while getting ETA certificate')
            return _get_error_template(str(ex))
        finally:
            session.logout()
            session.closeSession()

    @route.iot_route('/hw_l10n_eg_eta/sign', type='http', cors='*', csrf=False, methods=['POST'])
    def eta_sign(self, pin, access_token, invoices):
        """Check if the access_token is valid and sign the invoices accessing the usb key with the pin.

        :param pin: pin of the token
        :param access_token: token shared with the main odoo instance
        :param invoices: dictionary of invoices. Keys are invoices ids, value are the base64 encoded binaries to sign
        :return: json object with the signed invoices
        """
        if not _is_access_token_valid(access_token):
            return _get_error_template('unauthorized')
        session, error = _get_session(pin)
        if error:
            return error
        try:
            cert = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_CERTIFICATE)])[0]
            cert_id = session.getAttributeValue(cert, [PyKCS11.CKA_ID])[0]
            priv_key = session.findObjects([(PyKCS11.CKA_CLASS, PyKCS11.CKO_PRIVATE_KEY), (PyKCS11.CKA_ID, cert_id)])[0]

            invoice_dict = dict()
            invoices = json.loads(invoices)
            for invoice, eta_inv in invoices.items():
                to_sign = base64.b64decode(eta_inv)
                signed_data = session.sign(priv_key, to_sign, PyKCS11.Mechanism(PyKCS11.CKM_SHA256_RSA_PKCS))
                invoice_dict[invoice] = base64.b64encode(bytes(signed_data)).decode()

            payload = {
                'invoices': json.dumps(invoice_dict),
            }
            return json.dumps(payload)
        except Exception as ex:
            _logger.exception('Error while signing invoices')
            return _get_error_template(str(ex))
        finally:
            session.logout()
            session.closeSession()
