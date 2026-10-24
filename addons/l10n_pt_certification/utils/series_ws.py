import base64
import logging
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

_logger = logging.getLogger(__name__)

WSSE_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
WSU_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd'
SOAP_MSG_SECURITY_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0'
USERNAME_TOKEN_PROFILE_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0'

WSSE = '{%s}' % WSSE_NS
WSU = '{%s}' % WSU_NS


class ATUsernameToken:
    """
    WS-Security UsernameToken for the AT Series webservice.

    The AT requires the password to be RSA-encrypted with their public key, carried alongside a
    Nonce holding the encrypted Created timestamp. There is deliberately no plaintext path: the
    caller must supply the public key, so a missing certificate cannot silently downgrade a live
    credential to clear text.
    """

    def __init__(self, username, password, public_key_pem):
        self.username = username
        self.password = password
        self.public_key_pem = public_key_pem

    def apply(self, envelope, headers):
        security = envelope.find('.//' + WSSE + 'Security')
        if security is None:
            header = envelope.find('{http://schemas.xmlsoap.org/soap/envelope/}Header')
            if header is None:
                header = etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Header')
            security = etree.SubElement(header, WSSE + 'Security')

        username_token = security.find(WSSE + 'UsernameToken')
        if username_token is None:
            username_token = etree.SubElement(security, WSSE + 'UsernameToken')

        # Username always sent
        username_el = etree.SubElement(username_token, WSSE + 'Username')
        username_el.text = self.username

        # Password: always RSA-encrypted with the AT public key
        password_el = etree.SubElement(username_token, WSSE + 'Password')
        password_el.set('Type', '%s#PasswordText' % USERNAME_TOKEN_PROFILE_NS)
        password_el.text = self._rsa_encrypt(self.password)

        # AT WS-Security: Nonce = RSA-encrypted Created timestamp
        created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        created_el = etree.SubElement(username_token, WSU + 'Created')
        created_el.text = created
        nonce_el = etree.SubElement(username_token, WSSE + 'Nonce')
        nonce_el.set('EncodingType', '%s#Base64Binary' % SOAP_MSG_SECURITY_NS)
        nonce_el.text = self._rsa_encrypt(created)

        return envelope, headers

    def verify(self, envelope):
        pass

    def _rsa_encrypt(self, value):
        public_key = serialization.load_pem_public_key(self.public_key_pem)
        encrypted = public_key.encrypt(
            value.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            )
        )
        return base64.b64encode(encrypted).decode('ascii')
