import json
from base64 import b64encode
from contextlib import contextmanager
from requests import Session, PreparedRequest, Response

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged, freeze_time
from odoo.tools.misc import file_open


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']
FILE_PATH = 'account_peppol/tests/assets'

@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolMessage(TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

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
            'invoice_sending_method': 'peppol',
            'peppol_eas': '0208',
            'peppol_endpoint': '3141592654',
        }, {
            'name': 'Molly',
            'city': 'Namur',
            'email': 'Namur@company.com',
            'country_id': cls.env.ref('base.be').id,
            'invoice_sending_method': 'peppol',
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
                'accounting_supplier_party': '0198:dk16356706',
                'filename': 'test_incoming',
                'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()),
                'state': 'done' if not error else 'error',
                'direction': 'incoming',
                'document_type': 'Invoice',
            },
        }

        responses = {
            '/api/peppol/1/send_document': {'result': {
                'messages': [{'message_uuid': FAKE_UUID[0]}] * nr_invoices}},
            '/api/peppol/1/ack': {'result': {}},
            '/api/peppol/1/get_all_documents': {'result': {
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
                        'error': False if not error else 'Test error',
                    }
                ],
            }}
        }
        return proxy_documents, responses

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        yield self
        self.env.context = previous_context

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        response = Response()
        response.status_code = 200
        if r.url.endswith('iso6523-actorid-upis%3A%3A0208%3A0477472701'):
            response._content = b"""<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:0477472701</id:ParticipantIdentifier>'
            '<smp:ServiceMetadataReferenceCollection><smp:ServiceMetadataReference href="https://iap-services.odoo.com/iso6523-actorid-upis%3A%3A0208%3A0477472701/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1"/>'
            '</smp:ServiceMetadataReferenceCollection></smp:ServiceGroup>"""
            return response
        if r.url.endswith('iso6523-actorid-upis%3A%3A0208%3A3141592654'):
            response.status_code = 404
            return response
        if r.url.endswith('iso6523-actorid-upis%3A%3A0208%3A2718281828'):
            response._content = b"""<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0208:2718281828</id:ParticipantIdentifier>
            '<smp:ServiceMetadataReferenceCollection><smp:ServiceMetadataReference href="https://iap-services.odoo.com/iso6523-actorid-upis%3A%3A0208%3A0477472701/services/busdox-docid-qns%3A%3Aurn%3Aoasis%3Anames%3Aspecification%3Aubl%3Aschema%3Axsd%3AInvoice-2%3A%3AInvoice%23%23urn%3Acen.eu%3Aen16931%3A2017%23compliant%23urn%3Afdc%3Apeppol.eu%3A2017%3Apoacc%3Abilling%3A3.0%3A%3A2.1"/>'
            '</smp:ServiceMetadataReferenceCollection></smp:ServiceGroup>"""
            return response
        if r.url.endswith('iso6523-actorid-upis%3A%3A0198%3Adk16356706'):
            response._content = b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n<smp:ServiceGroup xmlns:wsa="http://www.w3.org/2005/08/addressing" xmlns:id="http://busdox.org/transport/identifiers/1.0/" xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:smp="http://busdox.org/serviceMetadata/publishing/1.0/"><id:ParticipantIdentifier scheme="iso6523-actorid-upis">0198:dk16356706</id:ParticipantIdentifier></smp:ServiceGroup>'
            return response

        url = r.path_url
        body = json.loads(r.body)
        if url == '/api/peppol/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['documents']))
        else:
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'))

        if url == '/api/peppol/1/get_document':
            uuid = body['params']['message_uuids'][0]
            response.json = lambda: {'result': {uuid: proxy_documents[uuid]}}
            return response

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def test_attachment_placeholders(self):
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move, sending_methods=['email'])
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

        # we don't want to email the xml file in addition to sending via peppol
        wizard.sending_methods = ['peppol']
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The document has been sent to the Peppol Access Point for processing')

    def test_send_peppol_alerts(self):
        # a warning should appear before sending invoices to an invalid partner
        move = self.create_move(self.invalid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue('peppol' in wizard.sending_methods)
        self.assertTrue('account_peppol_warning_partner' in wizard.alerts)
        self.assertTrue('account_peppol_demo_test_mode' in wizard.alerts)

        # however, if there's already account_edi_ubl_cii_configure_partner, the warning should not appear
        self.invalid_partner.peppol_endpoint = False
        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue('peppol' in wizard.sending_methods)
        self.assertTrue('account_edi_ubl_cii_configure_partner' in wizard.alerts)
        self.assertFalse('account_peppol_warning_partner' in wizard.alerts)

    def test_resend_error_peppol_message(self):
        # should be able to resend error invoices
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue('peppol' in wizard.sending_methods)
        with self._set_context({'error': True}):
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
            self.assertRecordValues(
                move, [{
                    'peppol_move_state': 'error',
                    'peppol_message_uuid': FAKE_UUID[0],
                }])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue('peppol' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')

    def test_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # peppol_move_state should be set to done
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_bis3')
        self.assertTrue('peppol' in wizard.sending_methods)

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

        wizard = self.create_send_and_print(move)
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
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'valid',  # should validate automatically
                'peppol_eas': '0208',
                'peppol_endpoint': '0477472701',
            }])

        new_partner.peppol_endpoint = '3141592654'
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'not_valid',
                'peppol_eas': '0208',
                'peppol_endpoint': '3141592654',
            }])

        new_partner.invoice_edi_format = False
        self.assertFalse(new_partner.peppol_verification_state)

        # the participant exists on the network but cannot receive XRechnung
        new_partner.write({
            'invoice_edi_format': 'xrechnung',
            'peppol_endpoint': '0477472701',
        })
        self.assertRecordValues(
            new_partner, [{
                'peppol_verification_state': 'not_valid_format',
                'peppol_eas': '0208',
                'peppol_endpoint': '0477472701',
            }])

    def test_peppol_send_multi_async(self):
        company_2 = self.setup_other_company()['company']
        company_2.write({
            'country_id': self.env.ref('base.be').id,
        })

        new_partner = self.env['res.partner'].create({
            'name': 'Deanna Troi',
            'city': 'Namur',
            'country_id': self.env.ref('base.be').id,
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': 'ubl_bis3',
        })
        new_partner.with_company(company_2).invoice_edi_format = False
        # partner is valid for company 1
        self.assertRecordValues(new_partner, [{
            'peppol_verification_state': 'valid',
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': 'ubl_bis3',
            'invoice_sending_method': 'peppol',
        }])
        # but not valid for company 2
        self.assertRecordValues(new_partner.with_company(company_2), [{
            'peppol_verification_state': False,
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'invoice_edi_format': False,
            'invoice_sending_method': 'peppol',
        }])
        move_1 = self.create_move(new_partner)
        move_2 = self.create_move(new_partner)
        move_3 = self.create_move(new_partner, company_2)
        (move_1 + move_2 + move_3).action_post()

        wizard = self.create_send_and_print(move_1 + move_2 + move_3)
        wizard.action_send_and_print()
        self.assertEqual((move_1 + move_2 + move_3).mapped('is_being_sent'), [True, True, True])
        # the cron is ran asynchronously and should be agnostic from the current self.env.company
        self.env.ref('account.ir_cron_account_move_send').with_company(company_2).method_direct_trigger()
        # only move 1 & 2 should be processed, move_3 is related to an invalid partner (with regard to company_2) thus should fail to send
        self.assertEqual((move_1 + move_2 + move_3).mapped('peppol_move_state'), ['processing', 'processing', 'to_send'])

    def test_available_peppol_sending_methods(self):
        company_us = self.setup_other_company()['company']  # not a valid Peppol country
        self.assertTrue('peppol' in self.valid_partner.with_company(self.env.company).available_peppol_sending_methods)
        self.assertFalse('peppol' in self.valid_partner.with_company(company_us).available_peppol_sending_methods)

    def test_available_peppol_edi_formats(self):
        self.valid_partner.invoice_sending_method = 'peppol'
        self.assertFalse('facturx' in self.valid_partner.available_peppol_edi_formats)
        self.valid_partner.invoice_sending_method = 'email'
        self.assertTrue('facturx' in self.valid_partner.available_peppol_edi_formats)
