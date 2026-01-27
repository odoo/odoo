import json
from base64 import b64encode
from contextlib import contextmanager
from lxml import etree
from unittest.mock import patch
from urllib import parse

from requests import PreparedRequest, Response, Session

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged, freeze_time
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.mail.tests.common import MailCommon

ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']
FILE_PATH = 'account_peppol/tests/assets'

@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolMessage(TestAccountMoveSendCommon, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')
        cls.mocked_incoming_invoice_fname = 'incoming_invoice'

        cls.env.company.write({
            'country_id': cls.env.ref('base.be').id,
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'account_peppol_proxy_state': 'receiver',
        })

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'peppol')
        cls.private_key = cls.env['certificate.key'].create({
            'name': 'Test key PEPPOL',
            'content': b64encode(file_open(f'{FILE_PATH}/private_key.pem', 'rb').read()),
        })
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key_id': cls.private_key.id,
            'refresh_token': FAKE_UUID[0],
        })

        cls.invalid_partner, cls.valid_partner = cls.env['res.partner'].create([{
            'name': 'Wintermute',
            'city': 'Charleroi',
            'country_id': cls.env.ref('base.be').id,
            'peppol_eas': '0208',
            'peppol_endpoint': '3141592654',
        }, {
            'name': 'Molly',
            'city': 'Namur',
            'email': 'Namur@company.com',
            'country_id': cls.env.ref('base.be').id,
            'peppol_eas': '0208',
            'peppol_endpoint': '2718281828',
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
                (0, 0, {
                    'name': 'line 1',
                    'product_id': self.product_a.id,
                }),
                (0, 0, {
                    'name': 'line 2',
                    'product_id': self.product_a.id,
                }),
            ],
        })

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
        url = r.path_url.lower()
        if r.path_url.startswith('/api/peppol/1/lookup'):
            peppol_identifier = parse.parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0].lower()
            url_quoted_peppol_identifier = parse.quote_plus(peppol_identifier)
            if peppol_identifier == '0208:0477472701':
                response.status_code = 200
                response.json = lambda: {
                    "result": {
                        'identifier': peppol_identifier,
                        'smp_base_url': "http://iap-services.odoo.com",
                        'ttl': 60,
                        'service_group_url': f'http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}',
                        'services': [
                            {
                                "href": f"http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1",
                                "document_id": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
                            },
                        ],
                    },
                }
                return response
            if peppol_identifier == '0208:2718281828':
                response.status_code = 200
                response.json = lambda: {
                    "result": {
                        'identifier': peppol_identifier,
                        'smp_base_url': "http://iap-services.odoo.com",
                        'ttl': 60,
                        'service_group_url': f'http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}',
                        'services': [
                            {
                                "href": f"http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1",
                                "document_id": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0::2.1",
                            }
                        ],
                    },
                }
                return response

            if peppol_identifier == '0198:dk16356706':
                response.status_code = 200
                response.json = lambda: {"result": {
                        'identifier': peppol_identifier,
                        'smp_base_url': "http://iap-services.odoo.com",
                        'ttl': 60,
                        'service_group_url': f'http://iap-services.odoo.com/iso6523-actorid-upis%3A%3A{url_quoted_peppol_identifier}',
                        'services': [],
                    },
                }
                return response
            else:
                response.status_code = 404
                response.json = lambda: {"error": {"code": "NOT_FOUND", "message": "no naptr record", "retryable": False}}
                return response

        body = json.loads(r.body)
        if url == '/api/peppol/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            num_invoices = len(body['params']['documents'])
            response.json = lambda: {
                'result': {
                    'messages': [{'message_uuid': FAKE_UUID[0]}] * num_invoices
                }
            }
            return response

        if url == '/api/peppol/1/ack':
            response.json = lambda: {'result': {}}
            return response

        if url == '/api/peppol/1/get_all_documents':
            response.json = lambda: {
                'result': {
                    'messages': [
                        {
                            'accounting_supplier_party': '0198:dk16356706',
                            'filename': 'test_incoming.xml',
                            'uuid': FAKE_UUID[1],
                            'state': 'done',
                            'direction': 'incoming',
                            'document_type': 'Invoice',
                            'sender': '0198:dk16356706',
                            'receiver': '0208:0477472701',
                            'timestamp': '2022-12-30',
                            'error': False if not cls.env.context.get('error') else 'Test error',
                        }
                    ],
                }
            }
            return response

        if url == '/api/peppol/1/get_document':
            uuid = body['params']['message_uuids'][0]
            if uuid == FAKE_UUID[0]:
                response_content = {
                    'accounting_supplier_party': False,
                    'filename': 'test_outgoing.xml',
                    'enc_key': '',
                    'document': '',
                    'state': 'done' if not cls.env.context.get('error') else 'error',
                    'direction': 'outgoing',
                    'document_type': 'Invoice',
                }
            elif uuid == FAKE_UUID[1]:
                response_content = {
                    'accounting_supplier_party': '0198:dk16356706',
                    'filename': 'test_incoming',
                    'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                    'document': b64encode(file_open(f'{FILE_PATH}/{cls.mocked_incoming_invoice_fname}', mode='rb').read()),
                    'state': 'done' if not cls.env.context.get('error') else 'error',
                    'direction': 'incoming',
                    'document_type': 'Invoice',
                }

            response.json = lambda: {'result': {uuid: response_content}}
            return response

        return super()._request_handler(s, r, **kw)

    def test_non_xml_compatible_characters(self):
        """
        Test that non xml compatible characters doesn't block Peppol Invoice sending
        """
        move = self.create_move(self.valid_partner)
        product_a = self._create_product(
            name='Test\x02Product',
            lst_price=1000.0,
            standard_price=800.0
        )
        move.invoice_line_ids[0].product_id = product_a
        move.action_post()

        wizard = self.create_send_and_print(move, sending_methods=['peppol'])
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The invoice has been sent to the Peppol Access Point. The following attachments were sent with the XML:')

    def test_attachment_placeholders(self):
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')

        # the ubl xml placeholder should be generated
        self._assert_mail_attachments_widget(wizard, [
            {
                'mimetype': 'application/pdf',
                'name': 'INV_2023_00001.pdf',
                'placeholder': True,
            },
            {
                'mimetype': 'application/xml',
                'name': 'INV_2023_00001_ubl_bis3.xml',
                'placeholder': True,
            },
        ])

        wizard.sending_methods = ['peppol']
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The invoice has been sent to the Peppol Access Point. The following attachments were sent with the XML:')

    def test_send_peppol_alerts_not_valid_partner(self):
        move = self.create_move(self.invalid_partner)
        self.invalid_partner.invoice_edi_format = 'ubl_bis3'
        move.action_post()
        wizard = self.create_send_and_print(move, default=True)

        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertEqual(self.invalid_partner.peppol_verification_state, 'not_valid')  # not on peppol at all
        self.assertFalse(wizard.sending_methods and 'peppol' in wizard.sending_methods)  # peppol is not checked
        self.assertTrue(wizard.sending_method_checkboxes['peppol']['readonly'])  # peppol is not possible to select
        self.assertFalse(wizard.alerts)  # there is no alerts

    @patch('odoo.addons.account_peppol.models.res_partner.ResPartner._check_document_type_support', return_value=False)
    def test_send_peppol_alerts_not_valid_format_partner(self, mocked_check):
        move = self.create_move(self.valid_partner)
        move.action_post()
        wizard = self.create_send_and_print(move, sending_methods=['peppol'])

        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertEqual(self.valid_partner.peppol_verification_state, 'not_valid_format')  # on peppol but can't receive bis3
        self.assertTrue('account_peppol_warning_partner' in wizard.alerts)

    def test_send_peppol_alerts_invalid_partner(self):
        """If there's already account_edi_ubl_cii_configure_partner, the warning should not appear."""
        move = self.create_move(self.invalid_partner)
        move.action_post()
        self.invalid_partner.peppol_endpoint = False
        wizard = self.create_send_and_print(move, default=True)
        self.assertFalse(wizard.sending_methods and 'peppol' in wizard.sending_methods)  # by default peppol is not selected for non-valid partners
        wizard.sending_method_checkboxes = {**wizard.sending_method_checkboxes, 'peppol': {'checked': True}}
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)
        self.assertTrue('account_edi_ubl_cii_configure_partner' in wizard.alerts)
        self.assertFalse('account_peppol_warning_partner' in wizard.alerts)

    def test_resend_error_peppol_message(self):
        # should be able to resend error invoices
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)
        with self._set_context({'error': True}):
            wizard.with_env(self.env).action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
            self.assertRecordValues(
                move, [{
                    'peppol_move_state': 'error',
                    'peppol_message_uuid': FAKE_UUID[0],
                }])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')

    def test_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # peppol_move_state should be set to done
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertRecordValues(move, [{
                'peppol_move_state': 'done',
                'peppol_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via peppol
        self.env.company.account_peppol_proxy_state = 'rejected'

        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, default=True)
        self.assertTrue('peppol' not in wizard.sending_method_checkboxes)

    def test_receive_error_peppol(self):
        # an error peppol message should be created
        with self._set_context({'error': True}):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

            move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
            self.assertRecordValues(
                move, [{
                    'peppol_move_state': 'error',
                    'move_type': 'in_invoice',
                }])

    def test_receive_success_peppol(self):
        # a correct move should be created
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(
            move, [{
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
            }])

    def test_received_bill_notification(self):
        peppol_purchase_journal = self.env.company.peppol_purchase_journal_id
        peppol_purchase_journal.incoming_einvoice_notification_email = 'oops_another_bill@example.com'
        self.env.company.email = 'hq@example.com'

        with self.mock_mail_gateway():
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        self.assertSentEmail(
            '"company_1_data" <hq@example.com>',
            ['oops_another_bill@example.com'],
            subject=f"{self.env.company.name} - New invoice in {peppol_purchase_journal.display_name} journal",
        )

    def test_peppol_document_retrieval_with_company_context(self):
        # Ensure that the bill creation is done using the move company/proxy user context

        other_company = self.setup_other_company()['company']
        self.env["ir.default"].create({
            'company_id': other_company.id,
            'field_id': self.env['ir.model.fields']._get('res.partner', 'company_id').id,
            'json_value': other_company.id,
        })
        initial_company = self.env.company
        self.env['account_edi_proxy_client.user']\
            .with_company(other_company)\
            .with_context(allowed_company_ids=[other_company.id, self.env.company.id])\
            ._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(
            move, [{
                'company_id': initial_company.id,
                'peppol_move_state': 'done',
                'move_type': 'in_invoice',
            }])

    def test_validate_partner(self):
        new_partner = self.env['res.partner'].create({
            'name': 'Deanna Troi',
            'city': 'Namur',
            'country_id': self.env.ref('base.be').id,
        })
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'not_verified',
                'peppol_eas': '0208',
                'peppol_endpoint': False,
            }])

        new_partner.peppol_endpoint = '0477472701'
        new_partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'valid',
                'peppol_eas': '0208',
                'peppol_endpoint': '0477472701',
            }])

        new_partner.peppol_endpoint = '3141592654'
        new_partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'not_valid',
                'peppol_eas': '0208',
                'peppol_endpoint': '3141592654',
            }])

        # the participant exists on the network but cannot receive XRechnung
        new_partner.write({
            'invoice_edi_format': 'xrechnung',
            'peppol_endpoint': '0477472701',
        })
        new_partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'not_valid_format',
                'peppol_eas': '0208',
                'peppol_endpoint': '0477472701',
            }])

    def test_peppol_send_multi_async(self):
        company_2 = self.setup_other_company()['company']
        company_2.write({
            'peppol_eas': '0230',
            'peppol_endpoint': 'C2584563200',
            'country_id': self.env.ref('base.be').id,
        })

        new_partner = self.env['res.partner'].create({
            'name': 'Deanna Troi',
            'city': 'Namur',
            'country_id': self.env.ref('base.be').id,
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': 'ubl_bis3',
        })

        # partner is valid for company 1
        self.assertRecordValues(new_partner, [{
            'peppol_verification_state': 'valid',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': 'ubl_bis3',
        }])
        # but not valid for company 2
        new_partner.with_company(company_2).invoice_edi_format = 'nlcius'
        new_partner.button_account_peppol_check_partner_endpoint(company=company_2)
        self.assertRecordValues(new_partner.with_company(company_2), [{
            'peppol_verification_state': 'not_valid_format',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': 'nlcius',
        }])
        move_1 = self.create_move(new_partner)
        move_2 = self.create_move(new_partner)
        move_3 = self.create_move(new_partner, company_2)
        (move_1 + move_2 + move_3).action_post()

        wizard = self.create_send_and_print(move_1 + move_2 + move_3)
        wizard.action_send_and_print()
        self.assertEqual((move_1 + move_2 + move_3).mapped('is_being_sent'), [True, True, True])
        # the cron is ran asynchronously and should be agnostic from the current self.env.company
        with self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_account_move_send').with_company(company_2).method_direct_trigger()
        # only move 1 & 2 should be processed, move_3 is related to an invalid partner (with regard to company_2) thus should not be sent
        self.assertRecordValues((move_1 + move_2 + move_3), [
            {'peppol_move_state': 'processing', 'is_move_sent': True},
            {'peppol_move_state': 'processing', 'is_move_sent': True},
            {'peppol_move_state': False, 'is_move_sent': True},  # only sent by email
        ])

    def test_peppol_send_multi_async_mixed(self):
        """Try to send invoices to partners with multiple sending methods each. """
        peppol_partner = self.env['res.partner'].create({
            'name': 'Peppol partner',
            'country_id': self.env.ref('base.be').id,
            'company_registry': '0477472701',
        })
        self.assertRecordValues(peppol_partner, [{
            'peppol_verification_state': 'not_verified',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
        }])
        not_peppol_partner = self.env['res.partner'].create({
            'name': 'Not Peppol partner',
            'country_id': self.env.ref('base.us').id,
        })
        self.assertEqual(not_peppol_partner.peppol_verification_state, 'not_verified')
        move_1 = self.create_move(peppol_partner)
        move_2 = self.create_move(not_peppol_partner)
        (move_1 + move_2).action_post()
        wizard = self.create_send_and_print(move_1 + move_2)
        self.assertEqual(peppol_partner.peppol_verification_state, 'valid')
        self.assertEqual(not_peppol_partner.peppol_verification_state, 'not_verified')
        wizard.action_send_and_print()
        self.assertEqual((move_1 + move_2).mapped('is_being_sent'), [True, True])
        with self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertRecordValues((move_1 + move_2), [
            {'peppol_move_state': 'processing', 'is_move_sent': True},
            {'peppol_move_state': False, 'is_move_sent': True},  # only sent by email
        ])

    def test_available_peppol_sending_methods(self):
        company_us = self.setup_other_company()['company']  # not a valid Peppol country
        self.assertTrue('peppol' in self.valid_partner.with_company(self.env.company).available_peppol_sending_methods)
        self.assertFalse('peppol' in self.valid_partner.with_company(company_us).available_peppol_sending_methods)

    def test_available_peppol_edi_formats(self):
        self.valid_partner.invoice_sending_method = 'peppol'
        self.assertFalse('facturx' in self.valid_partner.available_peppol_edi_formats)
        self.valid_partner.invoice_sending_method = 'email'
        self.assertTrue('facturx' in self.valid_partner.available_peppol_edi_formats)

    def test_peppol_default_ubl_bis3_single(self):
        """In single invoice sending, if a partner is set on 'by Peppol' sending method,
        and has no specific e-invoice format, we should default on BIS3
        and generate invoices without errors.
        """
        self.valid_partner.invoice_edi_format = False

        move = self.create_move(self.valid_partner)
        move.action_post()
        wizard = self.create_send_and_print(move, default=True)
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        wizard.action_send_and_print()
        self.assertTrue(move.ubl_cii_xml_id)
        self.assertEqual(move.peppol_move_state, 'processing')

    def test_peppol_default_ubl_bis3_multi(self):
        """In multi-sending, if a partner is set on 'by Peppol' sending method, and
        has no specific e-invoice format, we should default on BIS3
        and generate invoices without errors.
        """
        self.valid_partner.invoice_edi_format = False

        move_1 = self.create_move(self.valid_partner)
        move_2 = self.create_move(self.valid_partner)
        moves = (move_1 + move_2)
        moves.action_post()
        wizard = self.create_send_and_print(moves, default=True)
        self.assertEqual(wizard.summary_data, {
            'email': {'count': 2, 'label': 'by Email'},
            'peppol': {'count': 2, 'label': 'by Peppol'},
        })
        wizard.action_send_and_print()
        with self.enter_registry_test_mode():
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()

        self.assertEqual(len(moves.ubl_cii_xml_id), 2)
        self.assertEqual(moves.mapped('peppol_move_state'), ['processing', 'processing'])

    def test_silent_error_while_creating_xml(self):
        """When in multi/async mode, the generation of XML can fail silently (without raising).
        This needs to be reflected as an error and put the move in Peppol Error state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.valid_partner.invoice_edi_format = 'ubl_bis3'
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
        self.assertEqual(move_1.peppol_move_state, 'error')

    def test_peppol_branch_company_send(self):
        branch_spoiled, branch_independent = self.env['res.company'].create([
            {
                'name': 'BE Spoiled Kid',
                'country_id': self.env.ref('base.be').id,
                'parent_id': self.env.company.id,
                'peppol_eas': '0208',
                'peppol_endpoint': '0477472701',
                'account_peppol_proxy_state': 'receiver',
            },
            {
                'name': 'BE Independent Kid',
                'country_id': self.env.ref('base.be').id,
                'parent_id': self.env.company.id,
                'peppol_eas': '0208',
                'peppol_endpoint': '0477471111',
                'account_peppol_proxy_state': 'receiver',
            },
        ])
        self.cr.precommit.run()  # load the COA
        self.valid_partner.button_account_peppol_check_partner_endpoint()
        self.env['account_edi_proxy_client.user'].create([
            {
                'company_id': branch_spoiled.id,
                'id_client': ID_CLIENT.replace('x', 'a'),
                'proxy_type': 'peppol',
                'edi_mode': 'test',
                'edi_identification': self.env['account_edi_proxy_client.user']._get_proxy_identification(branch_spoiled, 'peppol'),
                'private_key_id': self.private_key.id,
                'refresh_token': FAKE_UUID[1],
            },
            {
                'company_id': branch_independent.id,
                'id_client': ID_CLIENT.replace('x', 'b'),
                'proxy_type': 'peppol',
                'edi_mode': 'test',
                'edi_identification': self.env['account_edi_proxy_client.user']._get_proxy_identification(branch_independent, 'peppol'),
                'private_key_id': self.private_key.id,
                'refresh_token': FAKE_UUID[1],
            }
        ])

        # Branch uses parent's active peppol connection
        spoiled_move = self.create_move(self.valid_partner, company=branch_spoiled)
        spoiled_move.action_post()
        wizard = self.create_send_and_print(spoiled_move, sending_methods=['peppol'])
        wizard.action_send_and_print()
        self.assertEqual(spoiled_move.peppol_move_state, 'processing')

        # Branch uses peppol configuration independent of their parent
        independent_move = self.create_move(self.valid_partner, company=branch_independent)
        independent_move.action_post()
        wizard = self.create_send_and_print(independent_move, sending_methods=['peppol'])
        wizard.action_send_and_print()
        self.assertEqual(independent_move.peppol_move_state, 'processing')

    def test_compute_available_peppol_eas_multi_partner(self):
        """Check _compute_available_peppol_eas works with multiple partners"""

        # Create multiple partners
        partners = self.env['res.partner'].create([
            {'name': 'Partner A'},
            {'name': 'Partner B'},
        ])
        partners._compute_available_peppol_eas()
        for partner in partners:
            self.assertFalse('odemo' in partner.available_peppol_eas)

    def test_send_self_billed_invoice_via_peppol(self):
        """Test sending a self-billed invoice (vendor bill) via Peppol.

        Self-billed invoices are vendor bills that can be sent via Peppol when
        the company has self-billing sending activated.
        """
        # Enable self-billing sending for the company
        self.env.company.peppol_activate_self_billing_sending = True
        self.valid_partner.invoice_edi_format = 'ubl_bis3'

        self_billing_journal = self.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

        # Create a vendor bill (in_invoice) that can be sent as self-billed
        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self_billing_journal.id,
            'company_id': self.env.company.id,
            'partner_id': self.valid_partner.id,
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'ref': 'Test vendor bill reference',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'vendor line 1',
                    'product_id': self.product_a.id,
                }),
                (0, 0, {
                    'name': 'vendor line 2',
                    'product_id': self.product_a.id,
                }),
            ],
        })
        vendor_bill.action_post()

        # Verify the bill is exportable as self-invoice
        self.assertTrue(vendor_bill._is_exportable_as_self_invoice())

        # Create and configure the send wizard
        wizard = self.create_send_and_print(vendor_bill, default=True)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)

        # Send the self-billed invoice
        wizard.action_send_and_print()

        # Verify the invoice was sent successfully
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertRecordValues(vendor_bill, [{
                'peppol_move_state': 'done',
                'peppol_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(vendor_bill.ubl_cii_xml_id))

    def test_self_billing_sending_constraints(self):
        """Test that self-billing sending constraints are properly handled."""
        self.valid_partner.invoice_edi_format = 'ubl_bis3'

        self_billing_journal = self.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self_billing_journal.id,
            'company_id': self.env.company.id,
            'partner_id': self.valid_partner.id,
            'date': '2023-01-01',
            'invoice_date': '2023-01-01',
            'ref': 'Test vendor bill reference',
            'invoice_line_ids': [
                (0, 0, {
                    'name': 'vendor line 1',
                    'product_id': self.product_a.id,
                }),
            ],
        })
        vendor_bill.action_post()

        # Verify the bill is exportable as self-invoice
        self.assertTrue(vendor_bill._is_exportable_as_self_invoice())

        # Test that the constraint 'not_sale_document' is removed for self-billed invoices
        wizard = self.create_send_and_print(vendor_bill, default=True)
        self.assertTrue(wizard.sending_methods and 'peppol' in wizard.sending_methods)

        # Test that vendor bills can be sent as soon as the format allows (bis3) and the journal is in self-billing
        self.create_send_and_print(vendor_bill, default=True)

    def test_receive_self_billed_invoice_from_peppol(self):
        """Test receiving a self-billed invoice from Peppol.

        Self-billed invoices received via Peppol should be created as out_invoice
        in the self-billing reception journal.
        """
        # Set up the 21% VAT sale tax which should be put on the invoice line
        tax_21 = self.percent_tax(21.0, type_tax_use='sale')

        # Set up the self-billing reception journal
        sale_journal = self.env['account.journal'].search([
            ('company_id', '=', self.env.company.id),
            ('type', '=', 'sale'),
        ], limit=1)
        self.env.company.peppol_self_billing_reception_journal_id = sale_journal
        cls = self.__class__
        cls.mocked_incoming_invoice_fname = 'incoming_self_billed_invoice'

        def restore_mocked_incoming_invoice_fname():
            cls.mocked_incoming_invoice_fname = 'incoming_invoice'
        self.addCleanup(restore_mocked_incoming_invoice_fname)

        # Receive the self-billed invoice (using existing mock data)
        # The mock data already includes a document that will be processed
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        # Verify the self-billed invoice was created correctly
        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{
            'peppol_move_state': 'done',
            'move_type': 'out_invoice',
            'journal_id': self.env.company.peppol_self_billing_reception_journal_id.id,
        }])

        self.assertRecordValues(move.line_ids, [
            {
                'name': 'product_a',
                'quantity': 1.0,
                'price_unit': 100.0,
                'tax_ids': tax_21.ids,
                'amount_currency': -100.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
            {
                'name': 'percent_21.0_(1)',
                'quantity': False,
                'price_unit': False,
                'tax_ids': [],
                'amount_currency': -21.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
            {
                'name': 'BILL/2017/01/0001',
                'quantity': False,
                'price_unit': False,
                'tax_ids': [],
                'amount_currency': 121.0,
                'currency_id': self.env.ref('base.EUR').id,
            },
        ])

    def test_automatic_invoicing_auto_update_partner_peppol_status(self):
        self.ensure_installed('sale')
        tax = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax)
        partner = self.env['res.partner'].create({
            'name': 'partner_be',
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
            'invoice_sending_method': 'peppol',
            'invoice_edi_format': 'ubl_bis3',
            'company_id': self.env.company.id,
            'country_id': self.env.ref('base.be').id,
        })
        self.env.user.group_ids |= self.env.ref('sales_team.group_sale_salesman')

        self.env['ir.config_parameter'].sudo().set_param('sale.automatic_invoice', True)
        so = self._create_sale_order_one_line(product_id=product, partner_id=partner)

        payment_method = self.env.ref('payment.payment_method_unknown')

        dummy_provider = self.env['payment.provider'].create({
            'name': "Dummy Provider",
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'payment_method_ids': [Command.set(payment_method.ids)],
            'allow_tokenization': True,
        })
        self._create_dummy_payment_method_for_provider(
            provider=dummy_provider,
            journal=self.company_data['default_journal_bank'],
        )
        transaction = self.env['payment.transaction'].create({
            'payment_method_id': payment_method.id,
            'amount': so.amount_total,
            'state': 'done',
            'provider_id': dummy_provider.id,
            'currency_id': so.currency_id.id,
            'reference': so.name,
            'partner_id': partner.id,
            'sale_order_ids': [Command.set(so.ids)],
        })
        transaction.sudo()._post_process()

        self.assertRecordValues(partner, [{'peppol_verification_state': 'valid'}])

    def test_send_email_then_peppol(self):
        """
        Test that the PDF is correctly embedded in the Peppol XML even if the PDF
        was already generated by a previous 'Send by Email' action.
        """
        move = self.create_move(self.valid_partner)
        move.action_post()
        wizard_email = self.create_send_and_print(move, sending_methods=['email'])
        wizard_email.action_send_and_print()
        self.assertTrue(move.invoice_pdf_report_id, "PDF should be generated after sending by email")

        wizard_peppol = self.create_send_and_print(move, sending_methods=['peppol'])
        self.assertEqual(wizard_peppol.invoice_edi_format, 'ubl_bis3')
        wizard_peppol.action_send_and_print()
        self.assertTrue(move.ubl_cii_xml_id, "UBL XML should be generated")

        root = etree.fromstring(move.ubl_cii_xml_id.raw)
        embedded_pdfs = root.xpath(
            '//cbc:EmbeddedDocumentBinaryObject[@mimeCode="application/pdf"]',
            namespaces={
                'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            }
        )
        self.assertTrue(
            embedded_pdfs and embedded_pdfs[0].text,
            "Peppol XML must embed the already-generated PDF"
        )
