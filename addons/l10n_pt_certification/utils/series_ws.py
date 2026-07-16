import base64
import logging
import os
import socket

from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from lxml import etree

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import zeep
from odoo.tools.zeep.exceptions import Fault

_logger = logging.getLogger(__name__)

WSSE_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
WSU_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd'
SOAP_MSG_SECURITY_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0'
USERNAME_TOKEN_PROFILE_NS = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0'

WSSE = '{%s}' % WSSE_NS
WSU = '{%s}' % WSU_NS


class ATUsernameToken:
    def __init__(self, username, password, public_key_pem=None):
        self.username = username
        self.password = password
        self.public_key_pem = public_key_pem

    def apply(self, envelope, headers):
        from lxml import etree as _etree

        security = envelope.find('.//' + WSSE + 'Security')
        if security is None:
            header = envelope.find('{http://schemas.xmlsoap.org/soap/envelope/}Header')
            if header is None:
                header = _etree.SubElement(envelope, '{http://schemas.xmlsoap.org/soap/envelope/}Header')
            security = _etree.SubElement(header, WSSE + 'Security')

        username_token = security.find(WSSE + 'UsernameToken')
        if username_token is None:
            username_token = _etree.SubElement(security, WSSE + 'UsernameToken')

        # Username always sent
        username_el = _etree.SubElement(username_token, WSSE + 'Username')
        username_el.text = self.username

        # Password: RSA-encrypted if AT public key is configured, plaintext otherwise
        password_el = _etree.SubElement(username_token, WSSE + 'Password')
        password_el.set('Type', '%s#PasswordText' % USERNAME_TOKEN_PROFILE_NS)
        if self.public_key_pem:
            password_el.text = self._rsa_encrypt(self.password)
            # AT WS-Security: Nonce = RSA-encrypted Created timestamp
            created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            created_el = _etree.SubElement(username_token, WSU + 'Created')
            created_el.text = created
            nonce_el = _etree.SubElement(username_token, WSSE + 'Nonce')
            nonce_el.set('EncodingType', '%s#Base64Binary' % SOAP_MSG_SECURITY_NS)
            nonce_el.text = self._rsa_encrypt(created)
        else:
            password_el.text = self.password

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


class L10nPtAtSeriesWS:
    def __init__(self, env, company):
        self.env = env
        comp = company.sudo()

        wsdl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'api', 'Comunicacao_Series.wsdl')

        # Endpoint overridable via system parameter for switching between test/production
        endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_pt_certification.at_series_ws_endpoint'
        ) or 'http://localhost:7001/seriesbo/SeriesWSService'
        self.testing_env = 'localhost' in endpoint

        # Load AT public key for WS-Security encryption if configured
        public_key_pem = None
        public_cert = comp.l10n_pt_at_ws_public_cert_id
        if public_cert and public_cert.pem_certificate:
            public_key_pem = base64.b64decode(public_cert.with_context(bin_size=False).pem_certificate)

        wsse_token = ATUsernameToken(comp.l10n_pt_at_ws_username, comp.l10n_pt_at_ws_password, public_key_pem)

        settings = zeep.Settings(strict=False)
        client = zeep.Client(wsdl_path, wsse=wsse_token, settings=settings)
        self.service = client.bind('SeriesWSService', 'SeriesWSPort')
        self.service._binding_options['address'] = endpoint

    def registar_serie(self, serie, tipoSerie, classeDoc, tipoDoc, numInicialSeq,
                       dataInicioPrevUtiliz, numCertSWFatur, meioProcessamento):
        try:
            response = self.service.registarSerie(
                serie=serie,
                tipoSerie=tipoSerie,
                classeDoc=classeDoc,
                tipoDoc=tipoDoc,
                numInicialSeq=numInicialSeq,
                dataInicioPrevUtiliz=dataInicioPrevUtiliz,
                numCertSWFatur=numCertSWFatur,
                meioProcessamento=meioProcessamento,
            )
        except Fault as e:
            _logger.error('AT SeriesWS registarSerie SOAP fault: %s', e)
            raise UserError(
                _("AT Series registration failed: %(error)s", error=str(e))
            ) from e
        except (socket.timeout, IOError) as e:
            msg = _("Could not connect to the AT webservice.")
            _logger.error(msg)
            raise UserError(msg) from e

        if not response or not hasattr(response, 'infoResultOper'):
            raise UserError(_("AT Series registration returned an unexpected response."))

        info_result = response.infoResultOper
        if info_result.codResultOper != 2001:
            raise UserError(
                _("AT Series registration error (%(code)s): %(message)s",
                  code=info_result.codResultOper,
                  message=info_result.msgResultOper or '')
            )

        info_serie = getattr(response, 'infoSerie', None)
        if not info_serie or not getattr(info_serie, 'codValidacaoSerie', None):
            raise UserError(_("AT Series registration succeeded but no validation code was returned."))

        return info_serie.codValidacaoSerie
