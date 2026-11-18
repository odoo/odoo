import base64
import datetime as dt
import json
from contextlib import contextmanager
from unittest.mock import patch

import requests
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.x509.oid import NameOID
from freezegun import freeze_time

from odoo.exceptions import LockError, RedirectWarning, UserError
from odoo.tests import tagged

from odoo.addons.l10n_pt_at_webservice.const import PT_AT_DOCUMENT_TYPE_MAPPING
from odoo.addons.l10n_pt_at_webservice.utils import series_ws
from odoo.addons.l10n_pt_certification.const import PT_CERTIFICATION_NUMBER
from odoo.addons.l10n_pt_certification.utils.hashing import SIGN_DEFAULT_ENDPOINT
from odoo.addons.l10n_pt_certification.tests.common import (
    SERIES_PREFIXES,
    TestL10nPtCommon,
)

# The proxy's route of each operation of the AT's series webservice.
ROUTES = {
    'register': 'registarSerie',
    'query': 'consultarSeries',
    'annul': 'anularSerie',
    'finalize': 'finalizarSerie',
}


def _certificate(valid_from=None, valid_until=None):
    """A throwaway RSA key and its self-signed X.509 certificate."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, '123456789')])
    now = dt.datetime.now(dt.timezone.utc)
    certificate = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from or now - dt.timedelta(days=1))
        .not_valid_after(valid_until or now + dt.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )
    return key, certificate


def _info(serie, code, state='A', kind='F', registered='2026-06-15'):
    """A series as the AT describes it (``infoSerie``), in the proxy's JSON."""
    return {
        'serie': serie, 'tipoSerie': kind, 'classeDoc': 'SI', 'tipoDoc': 'FT', 'numInicialSeq': 1, 'numFinalSeq': None,
        'dataInicioPrevUtiliz': '2026-06-15', 'seqUltimoDocEmitido': None, 'meioProcessamento': 'PI',
        'numCertSWFatur': int(PT_CERTIFICATION_NUMBER), 'codValidacaoSerie': code, 'dataRegisto': registered,
        'estado': state, 'motivoEstado': None, 'justificacao': None, 'dataEstado': '2026-06-15T10:00:00',
        'nifComunicou': '123456789',
    }


def _answer(result_code, message='OK', *infos):
    """The AT's answer to an operation, as the proxy relays it: ``infos`` (``_info``) and its result."""
    return {'codResultOper': result_code, 'msgResultOper': message, 'infoSerie': list(infos)}


def _error(code, **details):
    """The proxy's refusal, or its report that the AT gave no usable answer."""
    return {'error': code, **details}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtAtSeriesWebservice(TestL10nPtCommon):
    """
    A series is communicated to the AT through its webservice (Portaria 195/2020 art. 3), called
    through Odoo's IAP proxy: only the HTTP exchange with the proxy is replaced, by its answers. The
    call against the AT's test endpoint needs a taxpayer's credentials and Odoo's certificate, and
    stays manual.
    """

    extra_companies = ('branch',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.at_private_key, at_certificate = _certificate()
        cls.startClassPatcher(patch.object(series_ws, 'get_at_public_certificate', lambda: at_certificate))
        cls.ws_settings = {
            'l10n_pt_at_ws_env': 'test',
            'l10n_pt_at_ws_username': '123456789/1',
            'l10n_pt_at_ws_password': 'segredo',
        }

    def _configure_ws(self, **overrides):
        self.company_pt.write({**self.ws_settings, **overrides})

    @contextmanager
    def _at(self, **answers):
        """
        Odoo's IAP proxy, and the AT behind it, answering each operation with ``answers[operation]``:
        the AT's answer (``_answer``), the proxy's error (``_error``), or an exception raised by the
        transport to the proxy. Yields the calls received: ``(url, operation, payload)``.
        """
        received = []

        def handler(cls, session, request, **kwargs):
            operation = ROUTES[request.url.rsplit('/', 1)[1]]
            received.append((request.url, operation, json.loads(request.body)['params']))
            answer = answers[operation]
            if isinstance(answer, Exception):
                raise answer
            response = requests.Response()
            response.status_code, response.url, response.request = 200, request.url, request
            response._content = json.dumps({'jsonrpc': '2.0', 'id': None, 'result': answer}).encode()
            response.headers['Content-Type'] = 'application/json'
            return response

        with patch.object(type(self), '_request_handler', classmethod(handler)):
            yield received

    def _proxy_url(self, route):
        return f"{self.env['ir.config_parameter'].sudo().get_param('l10n_pt.iap_endpoint', SIGN_DEFAULT_ENDPOINT)}/series/{route}"

    def _new_series(self, **vals):
        return self.series_factory(**{'name': '2026B', 'at_code': False, **vals})

    def _registered(self, name, code, registered='2026-06-15'):
        """A series registered through the webservice."""
        self._configure_ws()
        with self._at(registarSerie=_answer(2001, 'OK', _info(name, code, registered=registered))):
            return self._new_series(name=name)

    # ---------------------------------------------------------------------------------------------
    # Registration
    # ---------------------------------------------------------------------------------------------

    def test_registration_params(self):
        """Every document type of a series has the AT's class and type; a training series is registered as such."""
        selection = [value for value, _label in self.env['l10n_pt.at.series']._fields['document_type']._description_selection(self.env)]
        self.assertFalse(set(selection) - set(PT_AT_DOCUMENT_TYPE_MAPPING), "every document type of a series must be mapped")
        for document_type, training, expected in (
            ('out_invoice', False, ('SI', 'FT', 'N')),
            ('out_receipt', False, ('SI', 'FS', 'N')),
            ('out_invoice_receipt', False, ('SI', 'FR', 'N')),
            ('out_refund', False, ('SI', 'NC', 'N')),
            ('debit_note', False, ('SI', 'ND', 'N')),
            ('payment_receipt', True, ('PY', 'RG', 'F')),
        ):
            with self.subTest(document_type=document_type):
                series = self._new_series(name=f'2026{SERIES_PREFIXES[document_type]}', document_type=document_type, training_series=training)
                params = series._l10n_pt_at_ws_get_registration_params()
                self.assertEqual((params['classeDoc'], params['tipoDoc'], params['tipoSerie']), expected)
                self.assertEqual((params['serie'], params['numInicialSeq'], params['meioProcessamento']), (series.name, 1, 'PI'))

    def test_start_date_never_before_today_in_lisbon(self):
        """The AT refuses a start of use before its today: the later of the series' start and today in Lisbon is sent."""
        series = self._new_series(date_start='2026-01-01')
        self.assertEqual(series._l10n_pt_at_ws_get_registration_params()['dataInicioPrevUtiliz'], dt.date(2026, 6, 15))
        self.assertEqual(series.date_start, dt.date(2026, 1, 1))
        future = self._new_series(name='2026C', date_start='2026-07-01')
        self.assertEqual(future._l10n_pt_at_ws_get_registration_params()['dataInicioPrevUtiliz'], dt.date(2026, 7, 1))
        with freeze_time('2026-07-31 23:30:00'):  # 00:30 on 1 August in Lisbon (summer time)
            self.assertEqual(series._l10n_pt_at_ws_get_registration_params()['dataInicioPrevUtiliz'], dt.date(2026, 8, 1))

    def test_register(self):
        """
        Registering sends registarSerie through the proxy to the AT's test environment, with the
        sealed UsernameToken, and stores the validation code and the registration date it returns;
        the test environment registers a training series.
        """
        series = self._new_series()  # created before the webservice is configured, so not registered
        self._configure_ws()
        with self._at(registarSerie=_answer(2001, 'OK', _info('2026B', 'AAJFJMVNTN', registered='2026-06-14'))) as received:
            series.action_register_at_series()
        self.assertEqual(series.at_code, 'AAJFJMVNTN')
        self.assertEqual(series.l10n_pt_at_ws_registration_date, dt.date(2026, 6, 14))
        self.assertTrue(series.training_series)
        [(url, operation, payload)] = received
        self.assertEqual((url, operation), (self._proxy_url('register'), 'registarSerie'))
        self.assertEqual(payload['environment'], 'test')
        self.assertEqual(payload['db_uuid'], self.env['ir.config_parameter'].sudo().get_param('database.uuid'))
        self.assertEqual(payload['params'], {
            'serie': '2026B', 'tipoSerie': 'F', 'classeDoc': 'SI', 'tipoDoc': 'FT', 'numInicialSeq': 1,
            'dataInicioPrevUtiliz': '2026-06-15', 'numCertSWFatur': int(PT_CERTIFICATION_NUMBER), 'meioProcessamento': 'PI',
        })
        self.assertEqual(sorted(payload['token']), ['created', 'nonce', 'password', 'username'])
        self.assertEqual(payload['token']['username'], '123456789/1')
        self.assertNotIn('segredo', json.dumps(payload), "the password only travels sealed")

    def test_username_token_shape(self):
        """
        The UsernameToken follows AT's scheme: Nonce is the RSA-encrypted AES-128 key of the request,
        which decrypts Password and Created (AES/ECB/PKCS5).
        """
        token = series_ws.seal_username_token('123456789/1', 'segredo')
        aes_key = self.at_private_key.decrypt(base64.b64decode(token['nonce']), padding.PKCS1v15())
        self.assertEqual(len(aes_key), 16)

        def decrypt(field):
            decryptor = Cipher(algorithms.AES(aes_key), modes.ECB()).decryptor()
            padded = decryptor.update(base64.b64decode(token[field])) + decryptor.finalize()
            return padded[:-padded[-1]].decode()

        self.assertEqual(token['username'], '123456789/1')
        self.assertEqual(decrypt('password'), 'segredo')
        self.assertEqual(decrypt('created'), '2026-06-15T10:00:00.000Z')

    def test_register_refused_without_configuration(self):
        """Without credentials, or offline, nothing is sent."""
        series = self._new_series()
        with self._at() as received:
            for overrides, message in (
                ({'l10n_pt_at_ws_username': False}, "credentials are not configured"),
                ({'l10n_pt_at_ws_env': 'offline'}, "webservice is offline"),
            ):
                with self.subTest(message=message):
                    self._configure_ws(**overrides)
                    with self.assertRaisesRegex(UserError, message):
                        series.action_register_at_series()
        self.assertFalse(received)
        self.assertFalse(series.at_code)

    def test_register_errors(self):
        """Each failure is one sentence naming its cause, never a traceback; nothing is stored."""
        series = self._new_series()
        self._configure_ws()
        for answer, message in (
            (_answer(4003, 'Campo serie inválido'), r"The AT refused the request \(4003\): Campo serie inválido"),
            (_answer(2001, 'OK'), "no validation code was returned"),
            (_error('error_at_fault', message='Utilizador ou senha inválidos'), "refused the request: Utilizador ou senha inválidos"),
            (_error('error_at_http', status=403), r"refused the connection \(HTTP 403\)\. Please contact Odoo support"),
            (_error('error_at_http', status=500), r"HTTP error \(500\)"),
            (_error('error_at_unreadable'), "could not be read"),
            (_error('error_at_tls'), "secure connection to the AT webservice failed"),
            (_error('error_at_timeout'), "did not answer in time"),
            (_error('error_at_unreachable'), "Could not connect to the AT webservice"),
            (_error('error_db_not_production'), "not a production database"),
            (_error('error_internal'), "could not handle the request"),
            (requests.exceptions.ReadTimeout('Read timed out'), "did not answer in time"),
            (requests.exceptions.ConnectionError('Connection refused'), "Could not connect to Odoo's AT webservice service: Connection refused"),
        ):
            with self.subTest(message=message), self._at(registarSerie=answer), self.assertRaisesRegex(UserError, message):
                series.action_register_at_series()
        self.assertFalse(series.at_code)

    def test_register_concurrently(self):
        """A series another transaction is registering is not sent again."""
        series = self._new_series()
        self._configure_ws()
        with self._at() as received, patch.object(type(series), 'lock_for_update', side_effect=LockError("locked")), \
                self.assertRaisesRegex(UserError, "being changed right now"):
            series.action_register_at_series()
        self.assertFalse(received)

    def test_auto_registration(self):
        """
        A series created with the webservice configured is registered at once; offline, without
        credentials, or with a code given, it is not. A series the AT refuses is still created,
        without code, with the AT's message stored and notified; registering it later clears it.
        """
        with self._at() as received:
            self.assertFalse(self._new_series(name='2026C').at_code)
            self._configure_ws(l10n_pt_at_ws_env='offline')
            self.assertFalse(self._new_series(name='2026D').at_code)
            self._configure_ws()
            self.assertEqual(self._new_series(name='2026E', at_code='MANUAL01').at_code, 'MANUAL01')
        self.assertFalse(received)
        with self._at(registarSerie=_answer(2001, 'OK', _info('2026F', 'AAAUTO0001'))):
            self.assertEqual(self._new_series(name='2026F').at_code, 'AAAUTO0001')
        refusal = _answer(4049, 'A data de início não pode ser anterior à data atual')
        with self._at(registarSerie=refusal), patch.object(type(self.env.user), '_bus_send') as notify:
            series = self._new_series(name='2026G')
        self.assertFalse(series.at_code)
        self.assertRegex(series.l10n_pt_at_ws_error, r"\(4049\): A data de início")
        notify.assert_called_once()
        self.assertEqual(notify.call_args.args[1]['type'], 'warning')
        with self._at(registarSerie=_answer(2001, 'OK', _info('2026G', 'AAAUTO0002'))):
            series.action_register_at_series()
        self.assertEqual(series.at_code, 'AAAUTO0002')
        self.assertFalse(series.l10n_pt_at_ws_error)

    def test_recover_code_already_registered(self):
        """
        A series the AT already registered (4001) takes the code of the AT's active series of the
        same name, class, type and kind; otherwise the AT's refusal is kept, and a code another
        series holds is refused.
        """
        self._configure_ws()
        already = _answer(4001, 'Série já registada')
        for name, query, expected in (
            ('2026R1', _answer(2002, 'OK', _info('2026R1', 'AARECOVER1', state='N'), _info('2026R1', 'AARECOVER2')), 'AARECOVER2'),
            ('2026R2', _answer(2002, 'OK', _info('2026R2', 'AARECOVER3', kind='N')), None),
            ('2026R3', _answer(4048, 'Não foram encontradas séries'), None),
            ('2026R4', _error('error_at_fault', message='Erro interno'), None),
        ):
            with self.subTest(name=name):
                self._configure_ws(l10n_pt_at_ws_env='offline')
                series = self._new_series(name=name)
                self._configure_ws()
                with self._at(registarSerie=already, consultarSeries=query) as received:
                    if expected:
                        series.action_register_at_series()
                    else:
                        with self.assertRaisesRegex(UserError, r"\(4001\): Série já registada"):
                            series.action_register_at_series()
                self.assertEqual(series.at_code or None, expected)
                self.assertEqual([operation for _url, operation, _payload in received], ['registarSerie', 'consultarSeries'])
        self._configure_ws(l10n_pt_at_ws_env='offline')
        series = self._new_series(name='2026R5')
        self._configure_ws()
        with self._at(registarSerie=already, consultarSeries=_answer(2002, 'OK', _info('2026R5', 'AARECOVER2'))), \
                self.assertRaisesRegex(UserError, "whose code AARECOVER2 is that of the series"):
            series.action_register_at_series()

    def test_branch_uses_root_configuration(self):
        """A branch shares its root's NIF: its series is registered with the root's configuration."""
        self._configure_ws()
        self.assertEqual(self.branch_pt.l10n_pt_at_ws_env, 'offline')
        with self._at(registarSerie=_answer(2001, 'OK', _info('2026BR', 'AABRANCH01'))) as received:
            series = self._new_series(name='2026BR', company_id=self.branch_pt.id)
        self.assertEqual(series.at_code, 'AABRANCH01')
        self.assertEqual((received[0][2]['environment'], received[0][2]['token']['username']), ('test', '123456789/1'))

    def test_series_created_from_posting(self):
        """The series created from the warning of a posting is registered, and the invoice is numbered with its code."""
        self._configure_ws()
        journal = self.env['account.journal'].create({'name': 'Vendas Loja', 'type': 'sale', 'code': 'LOJA'})
        invoice = self.make_invoice(journal_id=journal.id)
        with self.assertRaises(RedirectWarning) as cm:
            self.post(invoice)
        context = cm.exception.args[1]['context']
        name = context['default_name']
        with self._at(registarSerie=_answer(2001, 'OK', _info(name, 'AAWSCODE01'))):
            self.env['l10n_pt.at.series'].with_context(context).create({})
        self.issue(self.post(invoice))
        self.assertEqual(invoice.l10n_pt_atcud, 'AAWSCODE01-1')

    # ---------------------------------------------------------------------------------------------
    # The connection test
    # ---------------------------------------------------------------------------------------------

    def test_connection(self):
        """Test connection only queries the AT: success is a notification, a failure its sentence."""
        self._configure_ws()
        settings = self.env['res.config.settings'].with_company(self.company_pt).create({})
        for answer in (_answer(4048, 'Não foram encontradas séries'), _answer(2002, 'OK', _info('2026A', 'AACONN0001'))):
            with self._at(consultarSeries=answer) as received:
                action = settings.action_l10n_pt_at_ws_test_connection()
            self.assertEqual(action['params']['type'], 'success')
            self.assertEqual([operation for _url, operation, _payload in received], ['consultarSeries'])
        with self._at(consultarSeries=_error('error_at_fault', message='Utilizador ou senha inválidos')), self.assertRaisesRegex(UserError, "Utilizador ou senha inválidos"):
            settings.action_l10n_pt_at_ws_test_connection()

    # ---------------------------------------------------------------------------------------------
    # Annulment and finalisation
    # ---------------------------------------------------------------------------------------------

    def test_annul(self):
        """
        A series registered through the webservice today or yesterday, unused, can be annulled:
        anularSerie with motivo ER; it is kept, ended and without code, and cannot be registered again.
        """
        today_series = self._registered('2026N1', 'AAANUL0001')
        yesterday_series = self._registered('2026N2', 'AAANUL0002', registered='2026-06-14')
        old_series = self._registered('2026N3', 'AAANUL0003', registered='2026-06-13')
        by_hand = self._new_series(name='2026N4', at_code='MANUAL04')
        self.assertEqual(
            [s.l10n_pt_at_ws_can_annul for s in (today_series, yesterday_series, old_series, by_hand)],
            [True, True, False, False],
        )
        with patch.object(type(today_series), '_l10n_pt_get_used', lambda series: series.filtered(lambda s: s == yesterday_series)):
            yesterday_series.invalidate_recordset(['l10n_pt_at_ws_can_annul'])
            self.assertFalse(yesterday_series.l10n_pt_at_ws_can_annul)
            with self.assertRaisesRegex(UserError, "cannot be annulled"):
                yesterday_series.action_l10n_pt_at_ws_annul()

        with self._at(anularSerie=_answer(2003, 'Série anulada')) as received:
            today_series.action_l10n_pt_at_ws_annul()
        self.assertEqual(
            received[0][2]['params'],
            {'serie': '2026N1', 'classeDoc': 'SI', 'tipoDoc': 'FT', 'codValidacaoSerie': 'AAANUL0001', 'motivo': 'ER', 'declaracaoNaoEmissao': True},
        )
        self.assertRecordValues(today_series, [{
            'at_code': False, 'date_end': dt.date(2026, 6, 14), 'l10n_pt_at_ws_annulment_date': dt.date(2026, 6, 15), 'active': False,
        }])
        with self.assertRaisesRegex(UserError, "was annulled at the AT"):
            today_series.action_register_at_series()

        with self._at(anularSerie=_answer(4051, 'A série já não pode ser anulada')), self.assertRaisesRegex(UserError, r"\(4051\)"):
            yesterday_series.action_l10n_pt_at_ws_annul()
        self.assertEqual(yesterday_series.at_code, 'AAANUL0002')

    def test_finalize(self):
        """
        An ended series whose numbered documents are all issued is finalised with the number of its
        last issued one; its end can then no longer change.
        """
        self._configure_ws()
        journal = self.env['account.journal'].create({'name': 'Vendas Junho', 'type': 'sale', 'code': 'JUN'})
        series = self.series_factory(name='2026F', at_code='AAFINAL001', journal_id=journal.id, date_start='2026-06-01', date_end='2026-06-30')
        first, second = self.make_invoice(journal_id=journal.id), self.make_invoice(journal_id=journal.id)
        self.issue(self.post(first))
        self.post(second)
        self.assertEqual((first + second).l10n_pt_at_series_id, series)
        with freeze_time('2026-07-02'):
            series.invalidate_recordset(['l10n_pt_at_ws_can_finalize'])
            self.assertFalse(series.l10n_pt_at_ws_can_finalize, "an invoice is numbered but not issued yet")
            self.issue(second)
            series.invalidate_recordset(['l10n_pt_at_ws_can_finalize'])
            self.assertTrue(series.l10n_pt_at_ws_can_finalize)
            with self._at(finalizarSerie=_answer(2004, 'Série finalizada')) as received:
                series.action_l10n_pt_at_ws_finalize()
        self.assertEqual(received[0][2]['params']['seqUltimoDocEmitido'], second._l10n_pt_get_sequence_number())
        self.assertEqual(second._l10n_pt_get_sequence_number(), 2)
        self.assertEqual(series.l10n_pt_at_ws_finalization_date, dt.date(2026, 7, 2))
        with self.assertRaisesRegex(UserError, "end of a series finalised at the AT cannot be changed"):
            series.date_end = '2026-12-31'
        open_series = self.series_factory(name='2026G', at_code='AAFINAL002')
        self.assertFalse(open_series.l10n_pt_at_ws_can_finalize)
