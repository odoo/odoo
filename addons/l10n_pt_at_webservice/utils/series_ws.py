import base64
import os
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import padding as symmetric_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from lxml import etree

from odoo.exceptions import UserError
from odoo.tools.zeep.exceptions import TransportError

# The namespace of the AT's own example header, in which every element of the UsernameToken is
# expected, Created included.
WSSE_NS = 'http://schemas.xmlsoap.org/ws/2002/12/secext'
WSSE = '{%s}' % WSSE_NS
SOAP_ENV = '{http://schemas.xmlsoap.org/soap/envelope/}'


def raise_for_http_error(response, *args, **kwargs):
    """
    ``requests`` response hook: an HTTP error that is not a SOAP answer (a refused client
    certificate, a proxy's error page) is raised as a ``TransportError`` with its status, before
    zeep parses it. A SOAP fault, sent as XML, is left to zeep.
    """
    if response.status_code >= 400 and 'xml' not in response.headers.get('Content-Type', '').lower():
        raise TransportError(
            (response.reason or response.text[:200] or '').strip(),
            status_code=response.status_code,
            content=response.content,
        )


class ATUsernameToken:
    """
    WS-Security UsernameToken of the AT webservices, as the AT specifies it: each request draws a
    new AES-128 key, which encrypts the password and the creation time (AES/ECB/PKCS5), and is
    itself sent as the Nonce, encrypted with the AT's public key (RSA, PKCS#1 v1.5).

    There is deliberately no plaintext path: the caller must supply the AT's certificate, so a
    missing certificate cannot silently downgrade a live credential to clear text.
    """

    def __init__(self, username, password, certificate_pem):
        """
        :param certificate_pem: the AT's public key, as the X.509 certificate (PEM) the AT publishes.
        :raises ValueError: when ``certificate_pem`` is not a PEM certificate.
        """
        self.username = username
        self.password = password
        self.public_key = x509.load_pem_x509_certificate(certificate_pem).public_key()

    def apply(self, envelope, headers):
        header = envelope.find(SOAP_ENV + 'Header')
        if header is None:
            header = etree.Element(SOAP_ENV + 'Header')
            envelope.insert(0, header)
        security = header.find(WSSE + 'Security')
        if security is None:
            security = etree.SubElement(header, WSSE + 'Security', nsmap={'wss': WSSE_NS})

        key = os.urandom(16)
        created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        token = etree.SubElement(security, WSSE + 'UsernameToken')
        for tag, text in (
            ('Username', self.username),
            ('Password', self._aes_encrypt(key, self.password)),
            ('Nonce', base64.b64encode(self.public_key.encrypt(key, padding.PKCS1v15())).decode('ascii')),
            ('Created', self._aes_encrypt(key, created)),
        ):
            etree.SubElement(token, WSSE + tag).text = text
        return envelope, headers

    def verify(self, envelope):
        pass

    @staticmethod
    def _aes_encrypt(key, value):
        padder = symmetric_padding.PKCS7(algorithms.AES.block_size).padder()
        padded = padder.update(value.encode('utf-8')) + padder.finalize()
        encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()  # noqa: S305 - the AT's scheme
        return base64.b64encode(encryptor.update(padded) + encryptor.finalize()).decode('ascii')


class ATSeriesError(UserError):
    """The AT answered an operation with a result other than its success; ``code`` is its codResultOper."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


class ATSeriesClient:
    """
    The AT's series webservice (SeriesWSService, Portaria 195/2020), one method per operation. Each
    checks the AT's result code and returns what it answered, or raises an ``ATSeriesError``.
    Transport errors are left to the caller (see ``res.company._l10n_pt_at_ws_series_client``).
    """

    BINDING = '{http://at.gov.pt/}SeriesWSPortBinding'

    def __init__(self, env, service):
        """
        :param env: the environment the messages are translated in.
        :param service: the bound service (``odoo.tools.zeep.Client.create_service``).
        """
        self.env = env
        self.service = service

    def _check(self, response, success_code, operation):
        if not response or not getattr(response, 'infoResultOper', None):
            raise ATSeriesError(self.env._("%(operation)s returned an unexpected response.", operation=operation))
        result = response.infoResultOper
        if result.codResultOper != success_code:
            raise ATSeriesError(
                self.env._(
                    "%(operation)s error (%(code)s): %(message)s",
                    operation=operation, code=result.codResultOper, message=result.msgResultOper or '',
                ),
                code=result.codResultOper,
            )
        return response

    def register(self, **params):
        """registarSerie: the series registered, whose codValidacaoSerie is its validation code."""
        operation = self.env._("AT Series registration")
        response = self._check(self.service.registarSerie(**params), 2001, operation)
        info_serie = getattr(response, 'infoSerie', None)
        if not info_serie or not getattr(info_serie, 'codValidacaoSerie', None):
            raise ATSeriesError(self.env._("AT Series registration succeeded but no validation code was returned."))
        return info_serie

    def query(self, **filters):
        """consultarSeries: the AT's series matching ``filters`` (all optional); none when it finds none (4048)."""
        operation = self.env._("AT Series query")
        try:
            response = self._check(self.service.consultarSeries(**filters), 2002, operation)
        except ATSeriesError as e:
            if e.code == 4048:
                return []
            raise
        return list(response.infoSerie or [])

    def annul(self, **params):
        """anularSerie: the series annulled; its identifier can never be registered again."""
        return self._check(self.service.anularSerie(**params), 2003, self.env._("AT Series annulment"))

    def finalize(self, **params):
        """finalizarSerie: the series finalised; no document may be issued in it afterwards."""
        return self._check(self.service.finalizarSerie(**params), 2004, self.env._("AT Series finalisation"))
