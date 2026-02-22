import json
from base64 import b64encode
from contextlib import contextmanager
from requests import PreparedRequest, Response, Session
from unittest.mock import patch
from urllib.parse import parse_qs

from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon

from .common import FAKE_UUID, FILE_PATH, TestL10nFrPdpCommon


# TODO: some Peppol only sending tests (non-FR)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpMessage(TestL10nFrPdpCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.l10n_fr_pdp_proxy_state = 'receiver'
        cls.invalid_partner = cls.env['res.partner'].create([{
            'name': 'Wintermute',
            'city': 'Copenhagen',
            'country_id': cls.env.ref('base.dk').id,
            'invoice_sending_method': 'pdp',
            'vat': 'DK12345674',
        }])

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
            '/api/pdp/1/send_document': {'result': {'messages': [{'message_uuid': FAKE_UUID[0]}] * nr_invoices}},
            # '/api/pdp/1/get_document' is handled separately in _request_handler
            '/api/pdp/1/ack': {'result': {}},
            '/api/pdp/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': None,
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
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        yield self
        self.env.context = previous_context

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):

        if r.path_url.startswith('/api/pdp/1/annuaire_lookup?pdp_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['pdp_identifier'][0]
            return cls._get_annuaire_lookup_response(identifier, "96851575905823")
        elif r.path_url.startswith('/api/pdp/1/peppol_lookup?peppol_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return cls._get_peppol_lookup_response(identifier, "0208:0239843188")

        response = Response()
        response.status_code = 200
        url = r.path_url
        body = json.loads(r.body)
        if url == '/api/pdp/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['documents']))
        else:
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'))

        if url == '/api/pdp/1/get_document':
            uuid = body['params']['message_uuids'][0]
            response.json = lambda: {'result': {uuid: proxy_documents[uuid]}}
            return response

        if url not in responses:
            return super()._request_handler(s, r, **kw)
        response.json = lambda: responses[url]
        return response

    def test_pdp_attachment_placeholders(self):
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move, sending_methods=['email', 'pdp'])
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')

        # the ubl xml placeholder should be generated
        self._assert_mail_attachments_widget(wizard, [
            {
                'mimetype': 'application/pdf',
                'name': 'INV_2017_00001.pdf',
                'placeholder': True,
            },
            {
                'mimetype': 'application/xml',
                'name': 'INV_2017_00001_ubl_21_fr.xml',
                'placeholder': True,
            },
        ])

        wizard.sending_methods = ['pdp']
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The document has been sent to the PDP Access Point for processing')

    def test_send_pdp_not_receiver(self):
        self.env.company.l10n_fr_pdp_proxy_state = False
        move = self._create_french_invoice()
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(move.partner_id.pdp_verification_state, 'valid')
        self.assertTrue('pdp' not in wizard.sending_method_checkboxes)  # pdp checkbox not shown
        self.assertTrue('pdp' not in wizard.sending_methods)  # pdp is not checked by default

    def test_send_pdp_not_valid_format(self):
        partner = self.invalid_partner
        move = self._create_french_invoice()
        move.partner_id = partner
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(partner.pdp_verification_state, 'not_valid_format')
        self.assertTrue('pdp' not in wizard.sending_methods)  # pdp is not checked by default
        self.assertTrue(wizard.sending_method_checkboxes['pdp']['readonly'])  # can't select pdp
        self.assertFalse(wizard.alerts)  # there is no alerts

    def test_send_pdp_not_valid_partner(self):
        partner = self.invalid_partner
        partner.write({
            'pdp_identifier': '111111111',
            'invoice_edi_format': 'ubl_21_fr',
        })
        move = self._create_french_invoice()
        move.partner_id = partner
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(partner.pdp_verification_state, 'not_valid')
        self.assertTrue('pdp' not in wizard.sending_methods)  # pdp is not checked by default
        self.assertTrue(wizard.sending_method_checkboxes['pdp']['readonly'])  # can't select pdp
        self.assertFalse(wizard.alerts)  # there is no alerts

    def test_resend_error_pdp_message(self):
        # should be able to resend error invoices
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('pdp' in wizard.sending_methods)
        with self._set_context({'error': True}):
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_pdp_get_message_status()
            self.assertRecordValues(move, [{'pdp_move_state': 'error', 'pdp_message_uuid': FAKE_UUID[0]}])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('pdp' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_pdp_get_message_status()
        self.assertEqual(move.pdp_move_state, 'done')

    def test_pdp_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # pdp_move_state should be set to done
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('pdp' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_pdp_get_message_status()
        self.assertRecordValues(
            move,
            [{
                'pdp_move_state': 'done',
                'pdp_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_pdp_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via pdp
        self.env.company.l10n_fr_pdp_proxy_state = 'rejected'

        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertTrue('pdp' not in wizard.sending_method_checkboxes)

    def test_receive_error_pdp(self):
        # an error pdp message should be created
        with self._set_context({'error': True}):
            self.env['account_edi_proxy_client.user']._cron_pdp_get_new_documents()

            move = self.env['account.move'].search([('pdp_message_uuid', '=', FAKE_UUID[1])])
            self.assertRecordValues(move, [{'pdp_move_state': 'error', 'move_type': 'in_invoice'}])

    def test_receive_success_pdp(self):
        # a correct move should be created
        self.env['account_edi_proxy_client.user']._cron_pdp_get_new_documents()

        move = self.env['account.move'].search([('pdp_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{'pdp_move_state': 'done', 'move_type': 'in_invoice'}])

    def test_silent_error_while_creating_xml(self):
        """When in multi/async mode, the generation of XML can fail silently (without raising).
        This needs to be reflected as an error and put the move in PDP Error state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.partner_a.invoice_edi_format = 'ubl_21_fr'
        move_1 = self._create_french_invoice()
        move_2 = self._create_french_invoice()
        (move_1 + move_2).action_post()

        wizard = self.create_send_and_print(move_1 + move_2)
        with patch(
            'odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20.AccountEdiXmlUBL20._export_invoice_constraints',
            mocked_export_invoice_constraints
        ):
            wizard.action_send_and_print()
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertEqual(move_1.pdp_move_state, 'error')
