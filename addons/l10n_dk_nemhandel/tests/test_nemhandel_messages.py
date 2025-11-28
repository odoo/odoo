import json
from base64 import b64encode
from contextlib import contextmanager
from requests import PreparedRequest, Response, Session
from unittest.mock import patch
from urllib import parse

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged, freeze_time
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']
FILE_PATH = 'l10n_dk_nemhandel/tests/assets'


@freeze_time('2023-01-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNemhandelMessage(TestAccountMoveSendCommon):

    @classmethod
    @TestAccountMoveSendCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('l10n_dk_nemhandel.edi.mode', 'test')

        cls.env.company.write({
            'street': 'Boomvej 42',
            'nemhandel_identifier_type': '0088',
            'nemhandel_identifier_value': '5798009811512',
            'vat': 'DK58403288',
            'l10n_dk_nemhandel_proxy_state': 'receiver',
        })

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'nemhandel')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key Nemhandel',
            'content': b64encode(file_open(f'{FILE_PATH}/private_key.pem', 'rb').read()),
        })
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'nemhandel',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': FAKE_UUID[0],
        })

        cls.invalid_partner, cls.valid_partner = cls.env['res.partner'].create([{
            'name': 'Wintermute',
            'city': 'Copenhagen',
            'country_id': cls.env.ref('base.dk').id,
            'invoice_sending_method': 'nemhandel',
            'vat': 'DK12345674',
        }, {
            'name': 'Molly',
            'street': 'Arfvej 7',
            'city': 'Copenhagen',
            'email': 'Namur@company.com',
            'country_id': cls.env.ref('base.dk').id,
            'invoice_sending_method': 'nemhandel',
            'vat': 'DK12345666',
        }])

        cls.env['res.partner.bank'].create({
            'acc_number': '0144748555',
            'partner_id': cls.env.company.partner_id.id,
        })

    def create_move(self, partner, company=None):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': (company or self.env.company).id,
            'partner_id': partner.id,
            'date': '2023-01-01',
            'ref': 'Test reference',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line 1',
                    'product_id': self.product_a.id,
                }),
                Command.create({
                    'name': 'line 2',
                    'product_id': self.product_a.id,
                }),
            ],
        })

    @classmethod
    def _get_mock_data(cls, error=False, nr_invoices=1):
        proxy_documents = {
            FAKE_UUID[0]: {
                'accounting_supplier_party': False,
                'filename': 'test_outgoing.xml',
                'enc_key': '',
                'document': '',
                'state': 'done' if not error else 'error',
                'direction': 'outgoing',
                'document_type': 'Invoice',
            },
            FAKE_UUID[1]: {
                'accounting_supplier_party': '0184:16356706',
                'filename': 'test_incoming',
                'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()),
                'state': 'done' if not error else 'error',
                'direction': 'incoming',
                'document_type': 'Invoice',
            },
        }

        responses = {
            '/api/nemhandel/1/send_document': {'result': {'messages': [{'message_uuid': FAKE_UUID[0]}] * nr_invoices}},
            '/api/nemhandel/1/ack': {'result': {}},
            '/api/nemhandel/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': '0184:16356706',
                        'filename': 'test_incoming.xml',
                        'uuid': FAKE_UUID[1],
                        'state': 'done',
                        'direction': 'incoming',
                        'document_type': 'Invoice',
                        'sender': '0184:16356706',
                        'receiver': '0088:5798009811512',
                        'timestamp': '2022-12-30',
                        'error': False if not error else 'Test error',
                    }
                ],
            }}
        }
        return proxy_documents, responses

    @contextmanager
    def _set_context(self, other_context):
        cls = self.__class__
        env = cls.env(context=dict(cls.env.context, **other_context))
        with patch.object(cls, "env", env):
            yield

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.path_url.startswith('/api/peppol/1/lookup'):
            nemhandel_identifier = parse.parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0].lower()
            url_quoted_nemhandel_identifier = parse.quote_plus(nemhandel_identifier)
            if nemhandel_identifier.endswith('5798009811512'):
                response.status_code = 200
                response.json = lambda: {
                    "result": {
                        'identifier': nemhandel_identifier,
                        'smp_base_url': "https://smp-demo.nemhandel.dk",
                        'ttl': 60,
                        'service_group_url': f'http:///smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{url_quoted_nemhandel_identifier}',
                        'services': [
                            {
                                "href": f"https://smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{url_quoted_nemhandel_identifier}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3ACreditNote-2%3A%3ACreditNote%23%23OIOUBL-2.1%3A%3A2.1",
                                "document_id": "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##OIOUBL-2.1::2.1",
                            },
                        ],
                    },
                }
                return response
            if nemhandel_identifier.endswith('12345674'):
                response.status_code = 404
                response.json = lambda: {"error": {"code": "NOT_FOUND", "message": "no naptr record", "retryable": False}}
                return response
            if nemhandel_identifier.endswith('12345666'):
                response.status_code = 200
                response.json = lambda: {
                    "result": {
                        'identifier': nemhandel_identifier,
                        'smp_base_url': "https://smp-demo.nemhandel.dk",
                        'ttl': 60,
                        'service_group_url': f'http:///smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{url_quoted_nemhandel_identifier}',
                        'services': [
                            {
                                "href": f"https://smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{url_quoted_nemhandel_identifier}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3ACreditNote-2%3A%3ACreditNote%23%23OIOUBL-2.1%3A%3A2.1",
                                "document_id": "busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##OIOUBL-2.1::2.1",
                            },
                        ],
                    },
                }
                return response
            if nemhandel_identifier.endswith('16356706'):
                response.status_code = 200
                response.json = lambda: {
                    "result": {
                        'identifier': nemhandel_identifier,
                        'smp_base_url': "https://smp-demo.nemhandel.dk",
                        'ttl': 60,
                        'service_group_url': f'http:///smp-demo.nemhandel.dk/iso6523-actorid-upis%3A%3A{url_quoted_nemhandel_identifier}',
                        'services': [],
                    },
                }
                return response

        url = r.path_url.lower()
        body = json.loads(r.body)
        if url == '/api/nemhandel/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['documents']))
        else:
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'))

        if url == '/api/nemhandel/1/get_document':
            uuid = body['params']['message_uuids'][0]
            response.json = lambda: {'result': {uuid: proxy_documents[uuid]}}
            return response

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def test_nemhandel_attachment_placeholders(self):
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, sending_methods=['email', 'nemhandel'])
        self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')

        # the ubl xml placeholder should be generated
        self._assert_mail_attachments_widget(wizard, [
            {
                'mimetype': 'application/pdf',
                'name': 'INV_2023_00001.pdf',
                'placeholder': True,
            },
            {
                'mimetype': 'application/xml',
                'name': 'INV_2023_00001_oioubl_21.xml',
                'placeholder': True,
            },
        ])

        wizard.sending_methods = ['nemhandel']
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The document has been sent to the Nemhandel Access Point for processing')

    def test_send_nemhandel_alerts_not_valid_partner(self):
        move = self.create_move(self.invalid_partner)
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(self.invalid_partner.nemhandel_verification_state, 'not_valid')  # not on nemhandel at all
        self.assertFalse(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)  # nemhandel is not checked by default
        self.assertTrue(wizard.sending_method_checkboxes['nemhandel']['readonly'])  # can't select nemhandel
        self.assertFalse(wizard.alerts)  # there is no alerts

    def test_resend_error_nemhandel_message(self):
        # should be able to resend error invoices
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
        self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)
        with self._set_context({'error': True}):
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
            self.assertRecordValues(move, [{'nemhandel_move_state': 'error', 'nemhandel_message_uuid': FAKE_UUID[0]}])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
        self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
        self.assertEqual(move.nemhandel_move_state, 'done')

    def test_nemhandel_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # nemhandel_move_state should be set to done
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'oioubl_21')
        self.assertTrue(wizard.sending_methods and 'nemhandel' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_nemhandel_get_message_status()
        self.assertRecordValues(
            move,
            [{
                'nemhandel_move_state': 'done',
                'nemhandel_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_nemhandel_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via nemhandel
        self.env.company.l10n_dk_nemhandel_proxy_state = 'rejected'

        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertTrue('nemhandel' not in wizard.sending_method_checkboxes)

    def test_receive_error_nemhandel(self):
        # an error nemhandel message should be created
        with self._set_context({'error': True}):
            self.env['account_edi_proxy_client.user']._cron_nemhandel_get_new_documents()

            move = self.env['account.move'].search([('nemhandel_message_uuid', '=', FAKE_UUID[1])])
            self.assertRecordValues(move, [{'nemhandel_move_state': 'error', 'move_type': 'in_invoice'}])

    def test_receive_success_nemhandel(self):
        # a correct move should be created
        self.env['account_edi_proxy_client.user']._cron_nemhandel_get_new_documents()

        move = self.env['account.move'].search([('nemhandel_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{'nemhandel_move_state': 'done', 'move_type': 'in_invoice'}])

    def test_validate_partner_nemhandel(self):
        new_partner = self.env['res.partner'].create({
            'name': 'Deanna Troi',
            'city': 'Copenhagen',
            'country_id': self.env.ref('base.dk').id,
            'invoice_sending_method': 'nemhandel',

        })
        self.assertRecordValues(
            new_partner,
            [{
                'nemhandel_verification_state': False,
                'nemhandel_identifier_type': '0184',
                'nemhandel_identifier_value': False,
            }],
        )
        new_partner.write({
            'nemhandel_identifier_type': '0088',
            'nemhandel_identifier_value': '5798009811512',
        })
        self.assertEqual(new_partner.nemhandel_verification_state, 'valid')  # should validate automatically

        new_partner.write({
            'nemhandel_identifier_type': '0184',
            'nemhandel_identifier_value': '12345674',
        })

        self.assertEqual(new_partner.nemhandel_verification_state, 'not_valid')

    def test_nemhandel_edi_formats(self):
        self.valid_partner.invoice_sending_method = 'nemhandel'
        with self.assertRaises(UserError):
            self.valid_partner.invoice_edi_format = 'ubl_bis3'

        self.valid_partner.invoice_sending_method = 'email'
        self.valid_partner.invoice_edi_format = 'ubl_bis3'

    def test_nemhandel_silent_error_while_creating_xml(self):
        """When in multi/async mode, the generation of XML can fail silently (without raising).
        This needs to be reflected as an error and put the move in Nemhandel Error state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.valid_partner.invoice_edi_format = 'oioubl_21'
        move_1 = self.create_move(self.valid_partner)
        move_2 = self.create_move(self.valid_partner)
        (move_1 + move_2).action_post()

        wizard = self.create_send_and_print(move_1 + move_2)
        with patch(
            'odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20.AccountEdiXmlUBL20._export_invoice_constraints',
            mocked_export_invoice_constraints
        ), self.enter_registry_test_mode():
            wizard.action_send_and_print()
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertEqual(move_1.nemhandel_move_state, 'error')
