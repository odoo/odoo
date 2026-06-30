import datetime
import json

from base64 import b64encode
from contextlib import contextmanager
from freezegun import freeze_time
from unittest import mock
from unittest.mock import patch
from urllib.parse import parse_qs, quote_plus, urlsplit

from odoo import Command, fields
from odoo.tests.common import MockHTTPClient
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblCiiCommon


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = [
    'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
    'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz',
    'aaaaaaaa-bbbb-cccc-dddd-dddddddddddd',
]
FILE_PATH = 'l10n_fr_pdp/tests/test_files/assets'

PDP_PROXY_URL = 'https://pdp.test.odoo.com'


def _is_lookup_of(identifiers):
    return lambda r: (
        r.method == 'GET'
        and urlsplit(r.url).path.endswith('/lookup')
        and parse_qs(urlsplit(r.url).query)['peppol_identifier'][0] in identifiers
    )


@contextmanager
def mock_pdp_lookup_success(identifiers, ubl_services=True):
    def result(request):
        identifier = parse_qs(urlsplit(request.url).query)['peppol_identifier'][0]
        quoted = quote_plus(identifier)
        return {'result': {
            'identifier': identifier,
            'smp_base_url': "http://example.com/smp",
            'ttl': 60,
            'service_group_url': f"http://example.com/smp/iso6523-actorid-upis%3A%3A{quoted}",
            'services': [{
                'href': f"http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{quoted}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1",
                'document_id': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
            }] if ubl_services else [],
        }}

    with MockHTTPClient(matcher=_is_lookup_of(identifiers), return_json=result) as mock_response:
        yield mock_response


@contextmanager
def mock_pdp_lookup_not_found(identifiers):
    with MockHTTPClient(
        matcher=_is_lookup_of(identifiers),
        return_status=404,
        return_json={'error': {'code': "NOT_FOUND", 'message': "no naptr record", 'retryable': False}},
    ) as mock_response:
        yield mock_response


@contextmanager
def mock_pdp_annuaire_lookup(*valid_identifiers):
    def in_annuaire(request):
        return parse_qs(urlsplit(request.url).query)['pdp_identifier'][0] in valid_identifiers
    with MockHTTPClient(
        matcher=lambda r: r.method == 'GET' and urlsplit(r.url).path.endswith('/annuaire_lookup'),
        return_json=lambda r: {'result': {'in_annuaire': in_annuaire(r)}},
    ) as mock_response:
        yield mock_response


def _pdp_jsonrpc_mock(endpoint, result):
    return MockHTTPClient(
        method='POST',
        matcher=lambda r: r.headers.get('Content-Type') == 'application/json',
        url=f'{PDP_PROXY_URL}{endpoint}',
        return_json=(lambda r: {'result': result(r)}) if callable(result) else {'result': result},
    )


@contextmanager
def mock_pdp_registration(peppol_state='receiver'):
    with (
        _pdp_jsonrpc_mock('/api/pdp/1/connect', {'id_client': ID_CLIENT, 'refresh_token': FAKE_UUID}),
        _pdp_jsonrpc_mock('/api/pdp/1/register_receiver', {}),
        _pdp_jsonrpc_mock('/api/pdp/1/update_user', {}),
        _pdp_jsonrpc_mock('/api/pdp/1/cancel_peppol_registration', {}),
        _pdp_jsonrpc_mock('/api/pdp/2/participant_status', {'peppol_state': peppol_state}),
    ):
        yield


@contextmanager
def mock_pdp_send_document():
    def result(request):
        documents = json.loads(request.body)['params']['documents']
        return {'messages': [{'message_uuid': FAKE_UUID[0]}] * len(documents)}
    with _pdp_jsonrpc_mock('/api/pdp/1/send_document', result):
        yield


@contextmanager
def mock_pdp_send_response():
    # Yields the mock so the caller can read the sent request from ``mock.calls``.
    def result(request):
        reference_uuids = json.loads(request.body)['params']['reference_uuids']
        return {'messages': [{'message_uuid': FAKE_UUID[2]}] * len(reference_uuids)}
    with _pdp_jsonrpc_mock('/api/pdp/1/send_response', result) as send_response_mock:
        yield send_response_mock


@contextmanager
def mock_pdp_documents_retrieval(error=False):
    state = 'error' if error else 'done'
    documents = {
        FAKE_UUID[0]: {
            'accounting_supplier_party': False, 'filename': 'test_outgoing.xml', 'enc_key': '', 'document': '',
            'state': state, 'direction': 'outgoing', 'document_type': 'Invoice', 'origin_message_uuid': FAKE_UUID[0],
        },
        FAKE_UUID[1]: {
            'accounting_supplier_party': '0184:16356706', 'filename': 'test_incoming',
            'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='r').read(),
            'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()).decode(),
            'state': state, 'direction': 'incoming', 'document_type': 'Invoice', 'origin_message_uuid': FAKE_UUID[1],
        },
    }

    def get_document(request):
        uuid = json.loads(request.body)['params']['message_uuids'][0]
        return {uuid: documents[uuid]}

    with (
        _pdp_jsonrpc_mock('/api/pdp/1/ack', {}),
        _pdp_jsonrpc_mock('/api/pdp/1/get_all_ppf_documents', {}),
        _pdp_jsonrpc_mock('/api/pdp/1/get_all_documents', {'messages': [{
            'accounting_supplier_party': None, 'filename': 'test_incoming.xml', 'uuid': FAKE_UUID[1],
            'origin_message_uuid': FAKE_UUID[1], 'state': 'done', 'direction': 'incoming', 'document_type': 'Invoice',
            'sender': '0184:16356706', 'receiver': '0088:5798009811512', 'timestamp': '2022-12-30',
            'error': 'Test error' if error else False,
        }]}),
        _pdp_jsonrpc_mock('/api/pdp/1/get_document', get_document),
    ):
        yield


class TestL10nFrPdpCommon(TestUblCiiCommon, TestAccountMoveSendCommon):
    # Use a date after Feb decade/month end to place transaction/payment flows in grace/closed by default.
    TEST_TODAY = fields.Date.from_string('2025-03-05')
    TEST_INVOICE_DATE = fields.Date.from_string('2025-02-05')
    TEST_PAYMENT_DATE = fields.Date.from_string('2025-02-15')

    @classmethod
    @TestUblCiiCommon.setup_country('fr')
    def setUpClass(cls):
        super().setUpClass()

        cls.fakenow = datetime.datetime(2024, 12, 5)
        cls.startClassPatcher(freeze_time(cls.fakenow))

        cls.env['ir.config_parameter'].sudo().set_str('account_peppol.edi.mode', 'test')

        company = cls.company_data['company']
        company.write({
            'street': 'Rue Abbé Huet',
            'city': 'Rennes',
            'zip': '35043',
            'vat': 'FR91746948785',
            'phone': '+33612345678',
            'pdp_identifier': '968515759_96851575905899'  # Should set company_id, routing_scheme and routing_endpoint
        })
        cls.env['res.partner.bank'].create({
            'account_number': 'FR5000400440116243',
            'partner_id': cls.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'pdp')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key PDP',
            'content': cls.file_read(f'{FILE_PATH}/private_key.pem'),
        })
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'pdp',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': FAKE_UUID[0],
        })

        cls.partner_a = cls.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_SIRET': '96851575905808'},
            'invoice_edi_format': 'ubl_21_fr',
            'routing_identifier': '0225:968515759_96851575905808',
        })
        cls.partner_b.write({
            'name': 'SUPER BELGIAN PARTNER',
            'street': 'Rue du Paradis, 10',
            'zip': '6870',
            'city': 'Eghezee',
            'country_id': cls.env.ref('base.be').id,
            'phone': '061928374',
            'vat': 'BE0897223670',
            'invoice_edi_format': 'ubl_bis3',
            'routing_identifier': '0208:0239843188',
        })
        cls.startClassPatcher(patch(
            'odoo.addons.l10n_fr_pdp.models.pdp_flow.PdpFlow._get_pdp_proxy_user',
            return_value=False,
        ))

    # -------------------------------------------------------------------------
    # ACCOUNTING HELPERS
    # -------------------------------------------------------------------------

    def _create_french_invoice(self, move_type='out_invoice', **kwargs):
        tax_1 = self.env['account.chart.template'].ref('tva_acq_normale')
        tax_2 = self.env['account.chart.template'].ref('tva_acq_specifique')
        return self.env["account.move"].create({
            'move_type': move_type,
            'partner_id': self.partner_a.id,
            'partner_bank_id': self.env.company.partner_id.bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'narration': 'test narration',
            'ref': 'ref_move',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [Command.set(tax_1.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 1.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_2.ids)],
                }),
            ],
            **kwargs,
        })

    @classmethod
    def _send_patched(cls, invoice):
        valid_peppol_verification_state = mock.patch('odoo.addons.l10n_fr_pdp.models.res_partner.ResPartner._get_peppol_verification_state', return_value='valid')
        with valid_peppol_verification_state:
            # The successful verification sets the `invoice_sending_method` to `peppol` on the partner
            wizard = cls.env['account.move.send.wizard'] \
                .with_context(active_model=invoice._name, active_ids=invoice.ids) \
                .create({})
            wizard.action_send_and_print()
