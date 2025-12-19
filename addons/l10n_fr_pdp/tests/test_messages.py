import json
from base64 import b64encode
from contextlib import contextmanager
from requests import PreparedRequest, Response, Session
from unittest.mock import patch
from urllib.parse import parse_qs

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools.misc import file_open

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon

from .common import FAKE_UUID, FILE_PATH, TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpMessage(TestL10nFrPdpCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.account_peppol_proxy_state = 'receiver'
        cls.invalid_partner = cls.env['res.partner'].create([{
            'name': 'Wintermute',
            'city': 'Copenhagen',
            'country_id': cls.env.ref('base.dk').id,
            'invoice_sending_method': 'peppol',
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
                'origin_message_uuid': FAKE_UUID[0],
            },
            FAKE_UUID[1]: {
                'accounting_supplier_party': '0184:16356706',
                'filename': 'test_incoming',
                'enc_key': file_open(f'{FILE_PATH}/enc_key', mode='rb').read(),
                'document': b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read()),
                'state': 'done' if not error else 'error',
                'direction': 'incoming',
                'document_type': 'Invoice',
                'origin_message_uuid': FAKE_UUID[1],
            },
        }

        responses = {
            '/api/pdp/1/send_document': {'result': {'messages': [{'message_uuid': FAKE_UUID[0]}] * nr_invoices}},
            '/api/pdp/1/send_response': {'result': {'messages': [{'message_uuid': FAKE_UUID[2]}] * nr_invoices}},
            # '/api/pdp/1/get_document' is handled separately in _request_handler
            '/api/pdp/1/ack': {'result': {}},
            '/api/pdp/1/get_all_documents': {'result': {
                'messages': [
                    {
                        'accounting_supplier_party': None,
                        'filename': 'test_incoming.xml',
                        'uuid': FAKE_UUID[1],
                        'origin_message_uuid': FAKE_UUID[1],
                        'state': 'done',
                        'direction': 'incoming',
                        'document_type': 'Invoice',
                        'sender': '0184:16356706',
                        'receiver': '0088:5798009811512',
                        'timestamp': '2022-12-30',
                        'error': False if not error else 'Test error',
                    }
                ],
            }},
            '/api/pdp/1/get_all_ppf_documents': {'result': {}},
        }
        return proxy_documents, responses

    @contextmanager
    def _set_context(self, other_context):
        previous_context = self.env.context
        self.env.context = dict(previous_context, **other_context)
        try:
            yield self
        finally:
            self.env.context = previous_context

    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):

        if r.path_url.startswith('/api/pdp/1/annuaire_lookup?pdp_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['pdp_identifier'][0]
            return cls._get_annuaire_lookup_response(identifier, "968515759_96851575905823")
        elif r.path_url.startswith('/api/pdp/1/lookup?peppol_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return cls._get_peppol_lookup_response(identifier, "0208:0239843188")
        elif r.path_url.startswith('/api/peppol/1/lookup?peppol_identifier='):
            identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return cls._get_peppol_lookup_response(identifier, "0225:968515759_96851575905899")

        response = Response()
        response.status_code = 200
        url = r.path_url
        body = json.loads(r.body)
        if url == '/api/pdp/1/send_document':
            if not body['params']['documents']:
                raise UserError('No documents were provided')
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['documents']))
        elif url == '/api/pdp/1/send_response':
            if 'send_response_params' in cls.env.context:
                cls.env.context['send_response_params'] = body['params']
            proxy_documents, responses = cls._get_mock_data(cls.env.context.get('error'), nr_invoices=len(body['params']['reference_uuids']))
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

        wizard = self.create_send_and_print(move, sending_methods=['email', 'peppol'])
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

        wizard.sending_methods = ['peppol']
        wizard.action_send_and_print()
        self.assertEqual(self._get_mail_message(move).preview, 'The invoice has been sent to the Peppol Access Point. The following attachments were sent with the XML:')

    def test_send_pdp_not_receiver(self):
        self.env.company.account_peppol_proxy_state = False
        move = self._create_french_invoice()
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(move.partner_id.peppol_verification_state, 'valid')
        self.assertTrue('peppol' not in wizard.sending_method_checkboxes)  # peppol checkbox not shown
        self.assertTrue('peppol' not in wizard.sending_methods)  # peppol is not checked by default

    def test_send_pdp_not_valid_format(self):
        move = self._create_french_invoice()
        move.action_post()
        move.partner_id.invoice_edi_format = 'xrechnung'
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(move.partner_id.peppol_verification_state, 'not_valid_format')
        self.assertTrue('peppol' not in wizard.sending_methods)  # peppol is not checked by default
        self.assertTrue(wizard.sending_method_checkboxes['peppol']['readonly'])  # can't select peppol
        self.assertFalse(wizard.alerts)  # there is no alerts

    def test_send_pdp_not_valid_partner(self):
        partner = self.invalid_partner
        partner.write({
            'peppol_eas': '0225',
            'peppol_endpoint': '111111111',
            'invoice_edi_format': 'ubl_21_fr',
        })
        move = self._create_french_invoice()
        move.partner_id = partner
        move.action_post()
        wizard = self.env['account.move.send.wizard'].create({
            'move_id': move.id,
        })
        self.assertEqual(partner.peppol_verification_state, 'not_valid')
        self.assertTrue('peppol' not in wizard.sending_methods)  # peppol is not checked by default
        self.assertTrue(wizard.sending_method_checkboxes['peppol']['readonly'])  # can't select peppol
        self.assertFalse(wizard.alerts)  # there is no alerts

    def test_resend_error_pdp_message(self):
        # should be able to resend error invoices
        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('peppol' in wizard.sending_methods)
        with self._set_context({'error': True}):
            wizard.action_send_and_print()

            self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
            self.assertRecordValues(move, [{'peppol_move_state': 'error', 'peppol_message_uuid': FAKE_UUID[0]}])

        # we can't send the ubl document again unless we regenerate the pdf
        move.invoice_pdf_report_id.unlink()
        wizard = self.create_send_and_print(move)
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('peppol' in wizard.sending_methods)

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
        self.assertEqual(wizard.invoice_edi_format, 'ubl_21_fr')
        self.assertTrue('peppol' in wizard.sending_methods)

        wizard.action_send_and_print()

        self.env['account_edi_proxy_client.user']._cron_peppol_get_message_status()
        self.assertRecordValues(
            move,
            [{
                'peppol_move_state': 'done',
                'peppol_message_uuid': FAKE_UUID[0],
            }],
        )
        self.assertTrue(bool(move.ubl_cii_xml_id))

    def test_pdp_send_invalid_edi_user(self):
        # an invalid edi user should not be able to send invoices via pdp
        self.env.company.account_peppol_proxy_state = 'rejected'

        move = self._create_french_invoice()
        move.action_post()

        wizard = self.create_send_and_print(move)
        self.assertTrue('peppol' not in wizard.sending_method_checkboxes)

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
        This needs to be reflected as an error and put the move in 'error' peppol state.
        """
        def mocked_export_invoice_constraints(self, invoice, vals):
            return {'test_error_key': 'test_error_description'}

        self.partner_a.invoice_edi_format = 'ubl_21_fr'
        move_1 = self._create_french_invoice()
        move_2 = self._create_french_invoice()
        (move_1 + move_2).action_post()

        wizard = self.create_send_and_print(move_1 + move_2)
        with patch(
            'odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr.AccountEdiXmlUbl21Fr._export_invoice_constraints_new',
            mocked_export_invoice_constraints
        ):
            wizard.action_send_and_print()
            self.env.ref('account.ir_cron_account_move_send').method_direct_trigger()
        self.assertEqual(move_1.peppol_move_state, 'error')

    def _pay(self, move, amount=None):
        payment = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
            'payment_date': '2020-01-02',
            **({'amount': amount} if amount else {}),
        })._create_payments()
        self.assertTrue(payment.is_reconciled)
        self.assertFalse(payment.is_matched)
        payment.action_post()
        liquidity_lines, _counterpart_lines, _writeoff_lines = payment._seek_for_lines()

        statement_line = self.env['account.bank.statement.line'].create({
            'payment_ref': 'test',
            'journal_id': self.company_data['default_journal_bank'].id,
            'partner_id': move.partner_id.id,
            'amount': amount or payment.amount,
        })

        _st_liquidity_lines, st_suspense_lines, _st_other_lines = statement_line._seek_for_lines()
        st_suspense_lines.account_id = liquidity_lines.account_id
        (st_suspense_lines + liquidity_lines).reconcile()

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
        credit_note = move.reversal_move_ids
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
        payment.action_post()
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
        credit_note = move.reversal_move_ids
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
        self.assertFalse(move.pdp_ppf_move_state)
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
