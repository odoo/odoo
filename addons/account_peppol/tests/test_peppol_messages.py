import json
from base64 import b64encode
from contextlib import contextmanager
from freezegun import freeze_time
from requests import Session, PreparedRequest, Response

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open


ID_CLIENT = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
FAKE_UUID = ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy',
             'zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz']
FILE_PATH = 'account_peppol/tests/assets'

@freeze_time('2023-01-01')
@tagged('-at_install', 'post_install')
class TestPeppolMessage(TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env['ir.config_parameter'].sudo().set_param('account_peppol.edi.mode', 'test')

        cls.env.company.write({
            'country_id': cls.env.ref('base.be').id,
            'peppol_eas': '0208',
            'peppol_endpoint': '0477472701',
            'account_peppol_proxy_state': 'active',
        })

        edi_identification = cls.env['account_edi_proxy_client.user']._get_proxy_identification(cls.env.company, 'peppol')
        cls.proxy_user = cls.env['account_edi_proxy_client.user'].create({
            'id_client': ID_CLIENT,
            'proxy_type': 'peppol',
            'edi_mode': 'test',
            'edi_identification': edi_identification,
            'private_key': b64encode(file_open(f'{FILE_PATH}/private_key.pem', 'rb').read()),
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
            'country_id': cls.env.ref('base.be').id,
            'peppol_eas': '0208',
            'peppol_endpoint': '2718281828',
        }])

        cls.valid_partner.account_peppol_is_endpoint_valid = True
        cls.valid_partner.account_peppol_validity_last_check = '2022-12-01'

        cls.env['res.partner.bank'].create({
            'acc_number': '0144748555',
            'partner_id': cls.env.company.partner_id.id,
        })

    def create_move(self, partner):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
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
    def _get_mock_data(cls, error=False):
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
                'accounting_supplier_party': '0208:2718281828',
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
                'messages': [{'message_uuid': FAKE_UUID[0]}]}},
            '/api/peppol/1/ack': {'result': {}},
            '/api/peppol/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': '0208:2718281828',
                        'filename': 'test_incoming.xml',
                        'uuid': FAKE_UUID[1],
                        'state': 'done',
                        'direction': 'incoming',
                        'document_type': 'Invoice',
                        'sender': '0208:2718281828',
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
        if r.url.endswith('/iso6523-actorid-upis%3A%3A9925%3A0000000000'):
            return response

        proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'))
        url = r.path_url
        body = json.loads(r.body)
        if url == '/api/peppol/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')

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

        builder = self.valid_partner._get_edi_builder()
        filename = builder._export_invoice_filename(move)
        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
            checkbox_send_peppol=False,
        )

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
        wizard.checkbox_send_peppol = True
        self.assertFalse(bool(
            [file for file in wizard.mail_attachments_widget if file['name'] == filename]
        ))

    def test_send_peppol_invalid_partner(self):
        # a warning should appear before sending invoices to an invalid partner
        move = self.create_move(self.invalid_partner)
        move.action_post()

        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
            checkbox_send_peppol=True,
        )

        self.assertTrue(bool(wizard.peppol_warning))

    def test_resend_error_peppol_message(self):
        # should be able to resend error invoices
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
            checkbox_send_peppol=True,
        )
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
        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
            checkbox_send_peppol=True,
        )

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')

    def test_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # peppol_move_state should be set to done
        move = self.create_move(self.valid_partner)
        move.action_post()

        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
            checkbox_send_peppol=True,
        )

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

        wizard = self.create_send_and_print(
            move,
            checkbox_ubl_cii_xml=True,
        )
        self.assertRecordValues(wizard, [{'enable_peppol': False}])

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
