from base64 import b64decode, b64encode
from contextlib import contextmanager
from unittest.mock import patch

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from .common import FAKE_UUID, FILE_PATH
from .messages_common import TestPdpMessagesCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpMessage(TestPdpMessagesCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invalid_partner = cls.env['res.partner'].create([{
            'name': 'Wintermute',
            'city': 'Copenhagen',
            'country_id': cls.env.ref('base.dk').id,
            'vat': 'DK12345674',
        }])

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        try:
            yield self
        finally:
            self.env.context = previous_context

    def test_pdp_attachment_placeholders(self):
        move = self._create_french_invoice()
        move.action_post()
        partner = move.partner_id
        self.assertEqual(partner.ubl_cii_format, 'ubl_21_fr')
        filename = partner._get_edi_builder()._export_invoice_filename(move)

        wizard = self.create_send_and_print(move, checkbox_ubl_cii_xml=True, checkbox_send_peppol=False)

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

        # we don't want to email the xml file in addition to sending via peppol
        wizard.checkbox_send_peppol = True
        self.assertFalse(bool(
            [file for file in wizard.mail_attachments_widget if file['name'] == filename]
        ))
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The invoice has been sent to the Approved Platform. The following attachments were sent with the XML:')

    def test_send_pdp_not_receiver(self):
        self.env.company.account_peppol_proxy_state = False
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(move.partner_id.account_peppol_verification_label, 'valid')
        self.assertTrue(not wizard.enable_peppol)  # peppol checkbox not shown
        self.assertTrue(not wizard.checkbox_send_peppol)  # peppol is not checked by default

    def test_pdp_send_valid_pdp_partner_wrong_format(self):
        move = self._create_french_invoice()
        move.action_post()
        partner = move.partner_id
        self.assertEqual(partner.ubl_cii_format, 'ubl_21_fr')
        self.assertEqual(partner.account_peppol_verification_label, 'valid')
        self.assertTrue(partner.is_peppol_edi_format)

        partner.ubl_cii_format = 'ubl_bis3'
        self.assertEqual(partner.account_peppol_verification_label, 'not_valid_format')

        wizard = self.create_send_and_print(move)
        self.assertTrue(wizard.enable_peppol)  # peppol checkbox shown
        self.assertTrue(not wizard.checkbox_send_peppol)  # peppol is not checked by default
        self.assertEqual(wizard.peppol_warning, "For French regulated invoices, only the format 'France E-Invoicing (UBL 2.1)' is supported.Please check the following partners: SUPER FRENCH PARTNER")

    def test_send_pdp_not_valid_peppol_format(self):
        move = self._create_french_invoice()
        move.action_post()
        partner = move.partner_id
        partner.ubl_cii_format = 'zugferd'
        wizard = self.create_send_and_print(move)
        self.assertEqual(partner.account_peppol_verification_label, 'not_valid_format')
        self.assertTrue(not partner.is_peppol_edi_format)
        self.assertTrue(not wizard.enable_peppol)  # peppol checkbox not shown
        self.assertTrue(not wizard.checkbox_send_peppol)  # peppol is not checked by default
        self.assertEqual(wizard.peppol_warning, "For French regulated invoices, only the format 'France E-Invoicing (UBL 2.1)' is supported.Please check the following partners: SUPER FRENCH PARTNER")

    def test_send_pdp_not_valid_partner(self):
        partner = self.invalid_partner
        partner.write({
            'peppol_eas': '0225',
            'peppol_endpoint': '111111111',
            'ubl_cii_format': 'ubl_21_fr',
        })
        move = self._create_french_invoice()
        move.partner_id = partner
        move.action_post()
        wizard = self.create_send_and_print(move)
        self.assertEqual(partner.account_peppol_verification_label, 'not_valid')
        self.assertTrue(not wizard.checkbox_send_peppol)  # peppol is not checked by default
        self.assertTrue(wizard.enable_peppol)  # peppol checkbox is visible
        self.assertTrue(wizard.peppol_warning)  # there is a warning

    def test_resend_error_pdp_message(self):
        # should be able to resend error invoices
        move = self._create_french_invoice()
        move.action_post()
        partner = move.partner_id
        self.assertEqual(partner.ubl_cii_format, 'ubl_21_fr')

        wizard = self.create_send_and_print(move)
        self.assertTrue(wizard.enable_peppol)  # peppol checkbox show
        self.assertTrue(wizard.checkbox_send_peppol)  # peppol is checked by default
        with self._set_context({'error': True}):
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
            self.assertRecordValues(move, [{'peppol_move_state': 'error', 'peppol_message_uuid': FAKE_UUID[0]}])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move)
        self.assertEqual(partner.ubl_cii_format, 'ubl_21_fr')
        self.assertTrue(wizard.enable_peppol)  # peppol checkbox show
        self.assertTrue(wizard.checkbox_send_peppol)  # peppol is checked by default

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')

    def test_pdp_send_success_message(self):
        # should be able to send valid invoices correctly
        # attachment should be generated
        # peppol_move_state should be set to done
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(move.partner_id.ubl_cii_format, 'ubl_21_fr')
        self.assertTrue(wizard.enable_peppol)  # peppol checkbox show
        self.assertTrue(wizard.checkbox_send_peppol)  # peppol is checked by default

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertRecordValues(
            move,
            [{
                'peppol_move_state': 'done',
                'pdp_ppf_move_state': 'in_progress',
                'peppol_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_pdp_einvoicing_chatter_keeps_last_status_in_fetch(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'
        self.assertEqual(move.pdp_ppf_move_state, 'in_progress')

        message_count = len(move.message_ids)
        proxy_user = self.proxy_user.with_context(pdp_einvoicing_chatter_messages={})
        move.peppol_move_state = 'made_available'
        proxy_user._pdp_log_einvoicing_chatter(move, details=['First lifecycle detail'])
        move.peppol_move_state = 'done'
        move.pdp_ppf_move_state = 'sent'
        proxy_user._pdp_log_einvoicing_chatter(move, details=['Second lifecycle detail'])
        proxy_user._pdp_log_einvoicing_chatter(move)

        self.assertEqual(len(move.message_ids), message_count + 1)
        body = move.message_ids[0].body
        self.assertIn('PA Status:</strong> Done', body)
        self.assertIn('PPF Status:</strong> Sent', body)
        self.assertIn('First lifecycle detail', body)
        self.assertIn('Second lifecycle detail', body)

    def test_pdp_message_status_logs_once_per_updated_move(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'
        responses = self.env['account.peppol.response'].create([
            {
                'peppol_message_uuid': FAKE_UUID[1],
                'response_code': 'AB',
                'peppol_state': 'processing',
                'move_id': move.id,
                'pdp_flow_number': '2',
            },
            {
                'peppol_message_uuid': FAKE_UUID[2],
                'response_code': 'AB',
                'peppol_state': 'processing',
                'move_id': move.id,
                'pdp_flow_number': '2',
            },
        ])
        messages = {
            response.peppol_message_uuid: {
                'state': 'done',
                'document_type': 'CrossDomainAcknowledgementAndResponse',
            }
            for response in responses
        }
        uuid_to_record = {
            response.peppol_message_uuid: response
            for response in responses
        }

        message_count = len(move.message_ids)
        self.proxy_user._peppol_process_messages_status(messages, uuid_to_record)

        self.assertRecordValues(responses, [
            {'peppol_state': 'done'},
            {'peppol_state': 'done'},
        ])
        self.assertEqual(len(move.message_ids), message_count + 1)
        self.assertIn('E-Invoicing Status Update', move.message_ids[0].body)

    def test_pdp_einvoicing_chatter_error_keeps_status_update(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'
        self.assertEqual(move.pdp_ppf_move_state, 'in_progress')

        message_count = len(move.message_ids)
        proxy_user = self.proxy_user.with_context(pdp_einvoicing_chatter_messages={})
        proxy_user._pdp_log_einvoicing_chatter(move)
        proxy_user._pdp_log_einvoicing_chatter(
            move,
            ppf_status='error',
            errors=['The detailed PPF error message'],
            error_source='PPF Invoice',
        )

        self.assertEqual(len(move.message_ids), message_count + 2)
        body = move.message_ids[0].body
        self.assertIn('PPF Status:</strong> Error', body)
        self.assertIn('Errors from PPF Invoice:', body)
        self.assertIn('The detailed PPF error message', body)
        self.assertIn('PA Status:</strong> Done', move.message_ids[1].body)

    def test_pdp_einvoicing_chatter_keeps_distinct_errors(self):
        move = self._create_french_invoice()
        move.action_post()
        proxy_user = self.proxy_user.with_context(pdp_einvoicing_chatter_messages={})

        message_count = len(move.message_ids)
        proxy_user._pdp_log_einvoicing_chatter(
            move,
            pa_status='error',
            errors=['The detailed PA error message'],
            error_source='PA Lifecycle',
        )
        proxy_user._pdp_log_einvoicing_chatter(
            move,
            ppf_status='error',
            errors=['The detailed PPF error message'],
            error_source='PPF Lifecycle',
        )

        self.assertEqual(len(move.message_ids), message_count + 2)
        self.assertIn('Errors from PPF Lifecycle:', move.message_ids[0].body)
        self.assertIn('The detailed PPF error message', move.message_ids[0].body)
        self.assertIn('Errors from PA Lifecycle:', move.message_ids[1].body)
        self.assertIn('The detailed PA error message', move.message_ids[1].body)

    def test_pdp_einvoicing_chatter_empty_error_keeps_source(self):
        move = self._create_french_invoice()
        move.action_post()

        self.proxy_user._pdp_log_einvoicing_chatter(
            move,
            pa_status='error',
            errors=[],
            error_source='PA Lifecycle',
        )

        self.assertIn('Errors from PA Lifecycle:', move.message_ids[0].body)

    def test_pdp_einvoicing_pa_error_does_not_start_ppf(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'error'

        self.assertFalse(move.pdp_ppf_move_state)
        body = self.proxy_user._peppol_get_message_status_error_body(move, {
            'subject': 'Tax Extraction Error',
            'message': 'The detailed IAP error message',
        })
        self.assertIn('E-Invoicing Status Update', body)
        self.assertIn('PA Status:', body)
        self.assertIn('Error', body)
        self.assertNotIn('PPF Status:', body)
        self.assertIn('Errors from PA Invoice:', body)
        self.assertIn('The detailed IAP error message', body)
        self.assertNotIn('Tax Extraction Error', body)

    def test_pdp_einvoicing_ppf_invoice_error(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'

        self.proxy_user._pdp_import_tax_extract(FAKE_UUID[1], {
            'error': {
                'subject': 'Tax Extraction Error',
                'message': 'The detailed PPF error message',
            },
        }, move)

        self.assertEqual(move.pdp_ppf_move_state, 'error')
        body = move.message_ids[0].body
        self.assertIn('PPF Status:', body)
        self.assertNotIn('PA Status:', body)
        self.assertIn('Errors from PPF Invoice:', body)
        self.assertIn('The detailed PPF error message', body)

    def test_pdp_einvoicing_ppf_lifecycle_error(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'
        response = self.env['account.peppol.response'].create({
            'peppol_message_uuid': FAKE_UUID[1],
            'response_code': 'PD',
            'peppol_state': 'processing',
            'move_id': move.id,
            'pdp_flow_number': '2',
        })

        self.proxy_user._pdp_import_outgoing_response(FAKE_UUID[2], {
            'error': {'message': 'The detailed lifecycle error message'},
            'flow_number': '6',
            'origin_peppol_lifecycle_uuid': response.peppol_message_uuid,
        }, move)

        self.assertEqual(response.pdp_ppf_state, 'error')
        body = move.message_ids[0].body
        self.assertIn('Errors from PPF Lifecycle:', body)
        self.assertNotIn('PA Status:', body)
        self.assertIn('The detailed lifecycle error message', body)

    def test_pdp_einvoicing_refused_lifecycle_is_detail(self):
        move = self._create_french_invoice()
        move.action_post()
        move.peppol_message_uuid = FAKE_UUID[0]
        move.peppol_move_state = 'done'
        document = b'''<?xml version="1.0" encoding="UTF-8"?>
            <rsm:CrossDomainAcknowledgementAndResponse
                xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100"
                xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
                xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
                <rsm:AcknowledgementDocument>
                    <ram:IssueDateTime>
                        <udt:DateTimeString format="204">20241205000000</udt:DateTimeString>
                    </ram:IssueDateTime>
                    <ram:ReferenceReferencedDocument>
                        <ram:ProcessConditionCode>210</ram:ProcessConditionCode>
                        <ram:SpecifiedDocumentStatus>
                            <ram:ReasonCode>TRANSAC_INC</ram:ReasonCode>
                            <ram:Reason>Unknown transaction</ram:Reason>
                            <ram:IncludedNote>
                                <ram:Content>Lifecycle note</ram:Content>
                            </ram:IncludedNote>
                        </ram:SpecifiedDocumentStatus>
                    </ram:ReferenceReferencedDocument>
                </rsm:AcknowledgementDocument>
            </rsm:CrossDomainAcknowledgementAndResponse>'''
        symmetric_key = Fernet.generate_key()
        private_key = serialization.load_pem_private_key(
            b64decode(self.proxy_user.private_key),
            password=None,
        )
        encrypted_key = private_key.public_key().encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        attachment_domain = [
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
        ]
        attachment_count = self.env['ir.attachment'].search_count(attachment_domain)
        self.proxy_user._pdp_import_incoming_response(FAKE_UUID[1], {
            'document': b64encode(Fernet(symmetric_key).encrypt(document)),
            'enc_key': b64encode(encrypted_key),
            'flow_number': '2',
            'origin_ref_status_code': None,
            'origin_peppol_lifecycle_uuid': None,
            'state': 'done',
        }, move)

        body = move.message_ids[0].body
        self.assertIn('Details:', body)
        self.assertNotIn('Errors:', body)
        self.assertIn('[TRANSAC_INC] Unknown transaction', body)
        self.assertIn('Lifecycle note', body)
        self.assertEqual(self.env['ir.attachment'].search_count(attachment_domain), attachment_count)

    def test_pdp_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via pdp
        self.env.company.account_peppol_proxy_state = 'rejected'

        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertFalse(wizard.checkbox_send_peppol)

    def test_receive_error_pdp(self):
        # an error pdp message should be created
        with self._set_context({'error': True}):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

            move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
            self.assertRecordValues(move, [{'peppol_move_state': 'error', 'move_type': 'in_invoice'}])

    def test_receive_success_pdp(self):
        # a correct move should be created
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[1])])
        self.assertRecordValues(move, [{'peppol_move_state': 'done', 'move_type': 'in_invoice'}])

    def test_silent_error_while_creating_xml(self):
        """When in multi/async mode, the generation of XML can fail silently (without raising).
        This needs to be reflected by putting the move in the 'skipped' peppol state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.partner_a.ubl_cii_format = 'ubl_21_fr'
        move_1 = self._create_french_invoice()
        move_2 = self._create_french_invoice()
        (move_1 + move_2).action_post()

        wizard = self.create_send_and_print(move_1 + move_2, checkbox_download=False)
        with patch(
            'odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr.AccountEdiXmlUbl21Fr._export_invoice_constraints',
            mocked_export_invoice_constraints
        ):
            wizard.action_send_and_print()
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertEqual(move_1.peppol_move_state, 'skipped')

    def test_paid_lifecycle_credit_note_without_payment(self):
        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')
        move.pdp_ppf_move_state = 'sent'

        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((move.id,))],
                'journal_id': move.journal_id.id,
            }
        ).reverse_moves()
        credit_note = move.reversal_move_id
        credit_note.action_post()

        send_wizard2 = self.create_send_and_print(credit_note)
        send_wizard2.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(credit_note.peppol_move_state, 'done')
        credit_note.pdp_ppf_move_state = 'sent'

        self.assertFalse(move.amount_residual)
        self.assertEqual(move.payment_state, 'reversed')
        self.assertFalse(move.pdp_lifecycle_residual)

        self.assertFalse(credit_note.amount_residual)
        self.assertEqual(credit_note.payment_state, 'paid')
        self.assertFalse(credit_note.pdp_lifecycle_residual)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self.assertRaises(UserError):
            wizard.button_send()

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': credit_note.ids,
        })
        with self.assertRaises(UserError):
            wizard.button_send()

    def test_paid_lifecycle_in_payment(self):
        if self.env['account.move']._get_invoice_in_payment_state() != 'in_payment':
            # The 'in_payment' state does not exist; and it is just 'paid'
            self.skipTest('Accounting not installed')

        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')
        move.pdp_ppf_move_state = 'sent'

        self.assertFalse(move.pdp_lifecycle_residual)
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': '2020-01-02',
        })._create_payments()
        self.assertTrue(payment.is_reconciled)
        self.assertFalse(payment.is_matched)
        self.assertEqual(move.payment_state, 'in_payment')
        self.assertEqual(move.pdp_lifecycle_residual, 0)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self.assertRaises(UserError):
            wizard.button_send()

    def test_paid_lifecycle_fully_paid(self):
        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')
        move.pdp_ppf_move_state = 'sent'

        self.assertFalse(move.pdp_lifecycle_residual)
        self._pay(move)
        self.assertEqual(move.payment_state, 'paid')
        self.assertEqual(move.pdp_lifecycle_residual, move.amount_total)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self._set_context({'send_response_params': None}) as self_with_context:
            wizard.button_send()
            self.assertEqual(self_with_context.env.context['send_response_params'], {
                'lifecycle': True,
                'reference_uuids': ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'],
                'status': 'paid',
                'additional_info': {
                    move.peppol_message_uuid: {
                        'payments': [
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '1085.00', 'currency': 'EUR', 'tax_percent': '8.50'},
                        ],
                        'issue_datetime': '2024-12-05 00:00:00',
                    }
                }})
        self.assertFalse(move.pdp_lifecycle_residual)

    def test_paid_lifecycle_partially_paid(self):
        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')
        move.pdp_ppf_move_state = 'sent'

        self.assertFalse(move.pdp_lifecycle_residual)
        self._pay(move, 1000)
        self.assertEqual(move.payment_state, 'partial')
        self.assertEqual(move.pdp_lifecycle_residual, 1000)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self._set_context({'send_response_params': None}) as self_with_context:
            wizard.button_send()
            self.assertEqual(self_with_context.env.context['send_response_params'], {
                'lifecycle': True,
                'reference_uuids': ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'],
                'status': 'paid',
                'additional_info': {
                    move.peppol_message_uuid: {
                        'payments': [
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '400.00', 'currency': 'EUR', 'tax_percent': '8.50'},
                        ],
                        'issue_datetime': '2024-12-05 00:00:00',
                    }
                }})
        paid_response = move.peppol_response_ids
        self.assertRecordValues(paid_response, [{
            'peppol_state': 'processing',
            'pdp_flow_number': '2',
            'response_code': 'PD',
            'pdp_ppf_state': False,
            'pdp_payment_info': [
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '400.00', 'currency': 'EUR', 'tax_percent': '8.50'},
            ],
            'move_id': move.id,
        }])
        self.assertFalse(move.pdp_lifecycle_residual)
        self.assertEqual(move._pdp_get_paid_lifecycle_total_amount(), 1000)
        move._get_reconciled_amls().remove_move_reconcile()
        self.assertEqual(move._pdp_get_paid_lifecycle_total_amount(), 1000)
        self.assertEqual(move.pdp_lifecycle_residual, -1000)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self._set_context({'send_response_params': None}) as self_with_context:
            wizard.button_send()
            self.assertEqual(self_with_context.env.context['send_response_params'], {
                'lifecycle': True,
                'reference_uuids': ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'],
                'status': 'paid',
                'additional_info': {
                    move.peppol_message_uuid: {
                        'payments': [
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '-600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '-400.00', 'currency': 'EUR', 'tax_percent': '8.50'},
                        ],
                        'issue_datetime': '2024-12-05 00:00:00',
                    }
                }})
        self.assertEqual(move._pdp_get_paid_lifecycle_total_amount(), 0)
        self.assertFalse(move.pdp_lifecycle_residual)

    def test_paid_lifecycle_fully_paid_partially_by_credit_note(self):
        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')
        move.pdp_ppf_move_state = 'sent'

        self.assertFalse(move.pdp_lifecycle_residual)
        self._pay(move, 1000)
        self.assertEqual(move.payment_state, 'partial')
        self.assertEqual(move.pdp_lifecycle_residual, 1000)

        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((move.id,))],
                'journal_id': move.journal_id.id,
            }
        ).reverse_moves()
        credit_note = move.reversal_move_id
        credit_note.action_post()

        self.assertEqual(move.payment_state, 'paid')
        self.assertEqual(move.pdp_lifecycle_residual, 1000)

        wizard = self.env['pdp.response.wizard'].create({
            'status': 'PD',
            'move_ids': move.ids,
        })
        with self._set_context({'send_response_params': None}) as self_with_context:
            wizard.button_send()
            self.assertEqual(self_with_context.env.context['send_response_params'], {
                'lifecycle': True,
                'reference_uuids': ['yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'],
                'status': 'paid',
                'additional_info': {
                    move.peppol_message_uuid: {
                        'payments': [
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                            {'amount_changed': False, 'type_code': 'MEN', 'amount': '400.00', 'currency': 'EUR', 'tax_percent': '8.50'},
                        ],
                        'issue_datetime': '2024-12-05 00:00:00',
                    }
                }})
        paid_response = move.peppol_response_ids
        self.assertRecordValues(paid_response, [{
            'peppol_state': 'processing',
            'pdp_flow_number': '2',
            'response_code': 'PD',
            'pdp_ppf_state': False,
            'pdp_payment_info': [
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '400.00', 'currency': 'EUR', 'tax_percent': '8.50'},
            ],
            'move_id': move.id,
        }])
        self.assertFalse(move.pdp_lifecycle_residual)
        self.assertEqual(move._pdp_get_paid_lifecycle_total_amount(), 1000)

    def test_paid_lifecycle_cron(self):
        move = self._create_french_invoice()
        move.action_post()

        send_wizard = self.create_send_and_print(move)
        send_wizard.action_send_and_print()
        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertEqual(move.peppol_move_state, 'done')

        self.assertFalse(move.pdp_lifecycle_residual)
        self._pay(move)
        self.assertEqual(move.payment_state, 'paid')
        self.assertEqual(move.pdp_lifecycle_residual, move.amount_total)

        # We only sent the payment lifecycle automatically in case the Flow 1 succeeded
        self.assertEqual(move.pdp_ppf_move_state, 'in_progress')
        self.env.ref('l10n_fr_pdp.ir_cron_pdp_send_lifecycles').method_direct_trigger()
        self.assertFalse(move.peppol_response_ids)

        move.pdp_ppf_move_state = 'sent'
        self.env.ref('l10n_fr_pdp.ir_cron_pdp_send_lifecycles').method_direct_trigger()
        paid_response = move.peppol_response_ids
        self.assertRecordValues(paid_response, [{
            'peppol_state': 'processing',
            'pdp_flow_number': '2',
            'response_code': 'PD',
            'pdp_ppf_state': False,
            'pdp_payment_info': [
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '600.00', 'currency': 'EUR', 'tax_percent': '20.00'},
                {'amount_changed': False, 'type_code': 'MEN', 'amount': '1085.00', 'currency': 'EUR', 'tax_percent': '8.50'},
            ],
            'move_id': move.id,
        }])


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpMessageFacturX(TestPdpMessagesCommon):

    @classmethod
    def _get_mock_data(cls, error=False, nr_invoices=1):
        proxy_documents = {
            FAKE_UUID[0]: {
                'accounting_supplier_party': '0184:16356706',
                'filename': 'test_incoming',
                'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                'document': b64encode(file_open(f'{FILE_PATH}/document_factur_x_self_bill', mode='rb').read()),
                'state': 'done' if not error else 'error',
                'direction': 'incoming',
                'document_type': 'Factur-X',
                'origin_message_uuid': FAKE_UUID[0],
            }
        }

        responses = {
            '/api/pdp/1/ack': {'result': {}},
            '/api/pdp/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': None,
                        'filename': 'test_incoming.pdf',
                        'uuid': FAKE_UUID[0],
                        'origin_message_uuid': FAKE_UUID[0],
                        'state': 'done',
                        'direction': 'incoming',
                        'document_type': 'Factur-X',
                        'sender': '0184:16356706',
                        'receiver': '0088:5798009811512',
                        'timestamp': '2022-12-30',
                        'error': False if not error else 'Test error',
                    }
                ],
            }},
        }
        return proxy_documents, responses

    def test_receive_success_pdp_factur_x_self_billed(self):
        # An outgoing invoice should be created from the Factur-X format when it is self-billed.
        self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()

        move = self.env['account.move'].search([('peppol_message_uuid', '=', FAKE_UUID[0])])
        self.assertRecordValues(move, [{
            'peppol_move_state': 'done',
            'move_type': 'out_invoice',
            'amount_total': 24,
        }])
        self.assertNotEqual(move.partner_id.id, move.company_id.id)
        self.assertRecordValues(move.partner_id, [{
            'name': 'SUPER FRENCH PARTNER',
            'vat': 'FR23334175221',
        }])
