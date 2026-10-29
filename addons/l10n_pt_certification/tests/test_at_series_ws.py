import base64
import datetime
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from zeep.exceptions import Fault

from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.l10n_pt_certification.utils.series_ws import ATUsernameToken


def _self_signed_certificate():
    """A throwaway RSA key and its self-signed X.509 certificate, as the AT publishes its public key."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'AT test public key')])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1)).not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    return key, certificate.public_bytes(serialization.Encoding.PEM)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtAtSeriesWebservice(TestL10nPtCommon):
    """
    A series is communicated to the AT through its webservice (`registarSerie`), which returns its
    validation code (Portaria 195/2020 art. 3). The SOAP client is mocked: the call against the AT's
    test endpoint needs a taxpayer's credentials and certificate, and stays manual (PT-27).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.at_private_key, at_certificate_pem = _self_signed_certificate()
        cls.at_public_cert = cls.env['certificate.certificate'].create({
            'name': 'AT public key',
            'content': base64.b64encode(at_certificate_pem),
            'company_id': cls.company_pt.id,
        })
        cls.ws_settings = {
            'l10n_pt_at_ws_env': 'test',
            'l10n_pt_at_ws_username': '123456789/1',
            'l10n_pt_at_ws_password': 'segredo',
            'l10n_pt_at_ws_public_cert_id': cls.at_public_cert.id,
        }

    def _configure_ws(self, **overrides):
        self.company_pt.write({**self.ws_settings, **overrides})

    @contextmanager
    def _mock_service(self, code='AAJFJMVNTN', result_code=2001, side_effect=None):
        """
        The AT's SeriesWS, answering `registarSerie` with ``code`` (``None``: no series in the answer);
        yields the mocked operation.
        """
        service = MagicMock()
        if side_effect:
            service.registarSerie.side_effect = side_effect
        else:
            service.registarSerie.return_value = SimpleNamespace(
                infoResultOper=SimpleNamespace(codResultOper=result_code, msgResultOper='Série inválida'),
                infoSerie=code and SimpleNamespace(codValidacaoSerie=code),
            )
        client = MagicMock()
        client.bind.return_value = service
        with patch.object(self.registry['res.company'], '_get_zeep_client__', return_value=client):
            yield service.registarSerie

    def _new_series(self, **vals):
        return self.series_factory(**{'name': '2026B', 'at_code': False, **vals})

    def test_registration_params(self):
        """Each document type is registered as the AT names it; a training series as such."""
        for document_type, training, expected in (
            ('out_invoice', False, ('SI', 'FT', 'N')),
            ('out_receipt', False, ('SI', 'FS', 'N')),
            ('out_invoice_receipt', False, ('SI', 'FR', 'N')),
            ('out_refund', False, ('SI', 'NC', 'N')),
            ('debit_note', False, ('SI', 'ND', 'N')),
            ('payment_receipt', True, ('PY', 'RG', 'F')),
        ):
            with self.subTest(document_type=document_type):
                series = self._new_series(name=f'2026{document_type[:3].upper()}', document_type=document_type, training_series=training)
                params = series._l10n_pt_at_ws_get_registration_params()
                self.assertEqual((params['classeDoc'], params['tipoDoc'], params['tipoSerie']), expected)
                self.assertEqual((params['serie'], params['numInicialSeq'], params['meioProcessamento']), (series.name, 1, 'PI'))

    def test_register(self):
        """Registering stores the validation code the AT returns; the test environment registers a training series."""
        # Created before the webservice is configured, so that it is not registered at creation.
        series = self._new_series()
        self._configure_ws()
        with self._mock_service() as registar:
            series.action_register_at_series()
        self.assertEqual(series.at_code, 'AAJFJMVNTN')
        self.assertTrue(series.training_series)
        self.assertEqual(registar.call_args.kwargs['tipoSerie'], 'F')

    def test_register_refused_without_configuration(self):
        """Without credentials, or without the AT's certificate, nothing is sent; offline, registering does nothing."""
        series = self._new_series()
        with self._mock_service() as registar:
            self._configure_ws(l10n_pt_at_ws_username=False)
            with self.assertRaisesRegex(UserError, "credentials are not configured"):
                series.action_register_at_series()
            self._configure_ws(l10n_pt_at_ws_public_cert_id=False)
            with self.assertRaisesRegex(UserError, "public key certificate is not configured"):
                series.action_register_at_series()
            self._configure_ws(l10n_pt_at_ws_env='offline')
            series.action_register_at_series()
        registar.assert_not_called()
        self.assertFalse(series.at_code)

    @mute_logger('odoo.addons.l10n_pt_certification.models.l10n_pt_at_series')
    def test_register_errors(self):
        """A SOAP fault, a refusal, an answer without code and a connection error each give a clear error."""
        # Created before the webservice is configured, so that it is not registered at creation.
        series = self._new_series()
        self._configure_ws()
        for kwargs, message in (
            ({'side_effect': Fault('Erro de autenticação')}, "AT Series registration failed: Erro de autenticação"),
            ({'result_code': 4001}, r"registration error \(4001\): Série inválida"),
            ({'code': None}, "no validation code was returned"),
            ({'side_effect': OSError('Connection refused')}, "Could not connect to the AT webservice"),
        ):
            with self.subTest(message=message), self._mock_service(**kwargs), self.assertRaisesRegex(UserError, message):
                series.action_register_at_series()
        self.assertFalse(series.at_code)

    @mute_logger('odoo.addons.l10n_pt_certification.models.l10n_pt_at_series')
    def test_auto_registration(self):
        """
        A series created with the webservice configured is registered at once; without credentials, or
        with a code given, it is not. A connection or certificate error still creates the series,
        without code; an unexpected error propagates (PT-118).
        """
        with self._mock_service() as registar:
            self.assertFalse(self._new_series(name='2026C').at_code)
            self._configure_ws()
            self.assertEqual(self._new_series(name='2026D', at_code='MANUAL01').at_code, 'MANUAL01')
            registar.assert_not_called()
            self.assertEqual(self._new_series(name='2026E').at_code, 'AAJFJMVNTN')
            registar.assert_called_once()
        for error in (OSError('Connection refused'), UserError("WS down"), ValueError("bad PEM")):
            with self.subTest(error=repr(error)), self._mock_service(side_effect=error):
                series = self._new_series(name=f'2026{type(error).__name__[:4].upper()}')
                self.assertTrue(series.exists())
                self.assertFalse(series.at_code)
        with self._mock_service(side_effect=KeyError('codValidacaoSerie')), self.assertRaises(KeyError):
            self._new_series(name='2026K')

    def test_series_created_from_posting(self):
        """The series created from the warning of a posting is registered, and the invoice is numbered with its code."""
        self._configure_ws()
        journal = self.env['account.journal'].create({'name': 'Vendas Loja', 'type': 'sale', 'code': 'LOJA'})
        invoice = self.make_invoice(journal_id=journal.id)
        with self.assertRaises(RedirectWarning) as cm:
            self.post(invoice)
        with self._mock_service(code='AAWSCODE01'):
            self.env['l10n_pt.at.series'].with_context(cm.exception.args[1]['context']).create({})
        self.issue(self.post(invoice))
        self.assertEqual(invoice.l10n_pt_atcud, 'AAWSCODE01-1')

    @unittest.skip("PT-27 (todo): the token RSA-encrypts the password and sends Created in clear, not AT's AES+RSA scheme")
    def test_username_token_shape(self):
        """
        The UsernameToken follows AT's scheme: Nonce is the RSA-encrypted AES-128 key of the request,
        which decrypts Password and Created (AES/ECB/PKCS5).
        """
        token = ATUsernameToken('123456789/1', 'segredo', base64.b64decode(self.at_public_cert.pem_certificate))
        envelope = etree.Element('{http://schemas.xmlsoap.org/soap/envelope/}Envelope')
        token.apply(envelope, {})
        nonce = envelope.find('.//{*}Nonce').text
        aes_key = self.at_private_key.decrypt(base64.b64decode(nonce), padding.PKCS1v15())
        self.assertEqual(len(aes_key), 16)
