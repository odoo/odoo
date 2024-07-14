# -*- coding: utf-8 -*-
from .common import TestMxEdiCommon
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from freezegun import freeze_time

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCFDIInvoiceWorkflow(TestMxEdiCommon):

    def test_invoice_workflow(self):
        with freeze_time('2017-01-01'):
            invoice = self._create_invoice(invoice_date_due='2017-02-01')  # Force PPD

        # No pac found.
        self.env.company.l10n_mx_edi_pac = None
        with freeze_time('2017-01-05'):
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [
            {
                'move_id': invoice.id,
                'datetime': fields.Datetime.from_string('2017-01-05 00:00:00'),
                'message': "No PAC specified.",
                'state': 'invoice_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': None}])

        # Set back the PAC but make it raising an error.
        self.env.company.l10n_mx_edi_pac = 'solfact'
        with freeze_time('2017-01-06'), self.with_mocked_pac_sign_error():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [
            {
                'move_id': invoice.id,
                'datetime': fields.Datetime.from_string('2017-01-06 00:00:00'),
                'message': "turlututu",
                'state': 'invoice_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': None}])

        # The failing attachment remains accessible for the user.
        self.assertTrue(invoice.l10n_mx_edi_invoice_document_ids.attachment_id)

        # Sign.
        with freeze_time('2017-01-07'), self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-01-07 00:00:00'),
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'attachment_origin': False,
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])
        self.assertTrue(invoice.l10n_mx_edi_cfdi_attachment_id)
        self.assertTrue(invoice.l10n_mx_edi_invoice_document_ids.attachment_id)
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Cancel failed.
        self.env.company.l10n_mx_edi_pac = None
        with freeze_time('2017-02-01'):
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '02'}) \
                .action_cancel_invoice()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': invoice.id,
                'datetime': fields.Datetime.from_string('2017-02-01 00:00:00'),
                'message': "No PAC specified.",
                'state': 'invoice_cancel_failed',
                'sat_state': False,
                'cancellation_reason': '02',
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values,
        ])

        # Set back the PAC but make it raising an error.
        self.env.company.l10n_mx_edi_pac = 'solfact'
        with freeze_time('2017-02-06'), self.with_mocked_pac_cancel_error():
            invoice.l10n_mx_edi_invoice_document_ids.sorted()[0].action_retry()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': invoice.id,
                'datetime': fields.Datetime.from_string('2017-02-06 00:00:00'),
                'message': "turlututu",
                'state': 'invoice_cancel_failed',
                'sat_state': False,
                'cancellation_reason': '02',
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values,
        ])

        # Cancel.
        with freeze_time('2017-02-07'), self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '02'}) \
                .action_cancel_invoice()

        invoice.l10n_mx_edi_invoice_document_ids.invalidate_recordset(fnames=['cancel_button_needed'])
        sent_doc_values['cancel_button_needed'] = False

        cancel_doc_values = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-02-07 00:00:00'),
            'message': False,
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': False,
        }
        sent_doc_values['sat_state'] = 'skip'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'cancel',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])

        # Sign again.
        invoice.button_draft()
        invoice.action_post()
        with freeze_time('2017-03-10'), self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values2 = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-03-10 00:00:00'),
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Sat.
        with freeze_time('2017-04-01'), self.with_mocked_sat_call(lambda _x: 'valid'):
            self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(extra_domain=[('move_id.company_id', '=', self.env.company.id)])
        sent_doc_values2['sat_state'] = 'valid'
        cancel_doc_values['sat_state'] = 'valid'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Payment fully match but failed.
        payment1 = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'payment_date': '2017-06-01',
                'amount': 100.0,
            })\
            ._create_payments()
        with freeze_time('2017-06-02'), self.with_mocked_pac_sign_error():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': payment1.move_id.id,
                'datetime': fields.Datetime.from_string('2017-06-02 00:00:00'),
                'message': "turlututu",
                'state': 'payment_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Unreconcile the payment.
        # The document should disappear.
        payment1.move_id.line_ids.remove_move_reconcile()
        with freeze_time('2017-06-02'):
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Redo the reconciliation.
        # The document should be created again.
        (invoice + payment1.move_id).line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .reconcile()
        with freeze_time('2017-06-03'), self.with_mocked_pac_sign_error():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': payment1.move_id.id,
                'datetime': fields.Datetime.from_string('2017-06-03 00:00:00'),
                'message': "turlututu",
                'state': 'payment_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # In case of success, the document is updated.
        with freeze_time('2017-06-04'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        payment1_doc_values1 = {
            'move_id': payment1.move_id.id,
            'datetime': fields.Datetime.from_string('2017-06-04 00:00:00'),
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment1_doc_values1,
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Call again the method shouldn't change anything.
        with freeze_time('2017-06-04'), self.with_mocked_pac_sign_error():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment1_doc_values1,
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Create another payment and unreconcile the first payment.
        payment2 = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'payment_date': '2017-06-01',
                'amount': 100.0,
            })\
            ._create_payments()
        payment1.move_id.line_ids.remove_move_reconcile()
        with freeze_time('2017-07-01'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        payment2_doc_values1 = {
            'move_id': payment2.move_id.id,
            'datetime': fields.Datetime.from_string('2017-07-01 00:00:00'),
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment2_doc_values1,
            payment1_doc_values1,
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Fail to cancel the invoice.
        with freeze_time('2017-07-10'), self.with_mocked_pac_cancel_error():
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '02'}) \
                .action_cancel_invoice()
        cancel_doc_values2 = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-07-10 00:00:00'),
            'message': "turlututu",
            'state': 'invoice_cancel_failed',
            'sat_state': False,
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': True,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values2,
            payment2_doc_values1,
            payment1_doc_values1,
            sent_doc_values2,
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Reconcile again the first payment. Since this reconciliation has already been sent to the SAT, nothing
        # is updated.
        (invoice + payment1.move_id).line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .reconcile()
        with freeze_time('2017-07-11'), self.with_mocked_pac_sign_error():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(
            invoice.l10n_mx_edi_invoice_document_ids.sorted(lambda x: (x.datetime, x.move_id.id), reverse=True),
            [
                cancel_doc_values2,
                payment2_doc_values1,
                payment1_doc_values1,
                sent_doc_values2,
                cancel_doc_values,
                sent_doc_values,
            ],
        )
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Cancel successfully the invoice.
        with freeze_time('2017-07-12'), self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '02'}) \
                .action_cancel_invoice()

        invoice.l10n_mx_edi_invoice_document_ids.invalidate_recordset(fnames=['cancel_button_needed'])
        sent_doc_values2['cancel_button_needed'] = False

        cancel_doc_values2.update({
            'datetime': fields.Datetime.from_string('2017-07-12 00:00:00'),
            'message': False,
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': False,
        })
        self.assertRecordValues(
            invoice.l10n_mx_edi_invoice_document_ids.sorted(lambda x: (x.datetime, x.move_id.id), reverse=True),
            [
                cancel_doc_values2,
                payment2_doc_values1,
                payment1_doc_values1,
                sent_doc_values2,
                cancel_doc_values,
                sent_doc_values,
            ],
        )
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'cancel'}])

        with freeze_time('2017-07-12'), self.with_mocked_sat_call(lambda x: 'cancelled' if x.move_id == invoice else 'valid'):
            self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(extra_domain=[('move_id.company_id', '=', self.env.company.id)])
        cancel_doc_values2['sat_state'] = 'cancelled'
        payment2_doc_values1['sat_state'] = 'valid'
        payment1_doc_values1['sat_state'] = 'valid'
        self.assertRecordValues(
            invoice.l10n_mx_edi_invoice_document_ids.sorted(lambda x: (x.datetime, x.move_id.id), reverse=True),
            [
                cancel_doc_values2,
                payment2_doc_values1,
                payment1_doc_values1,
                sent_doc_values2,
                cancel_doc_values,
                sent_doc_values,
            ],
        )
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'cancel'}])

    def test_invoice_sent_after_paid(self):
        invoice = self._create_invoice(invoice_date_due='2017-01-01')
        self.assertRecordValues(invoice, [{'l10n_mx_edi_payment_policy': 'PUE'}])

        # Pay.
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'payment_date': '2017-06-01',
                'amount': 100.0,
            })\
            ._create_payments()

        # Sign.
        with freeze_time('2017-01-07'), self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-01-07 00:00:00'),
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_update_payments_needed': True}])

        with freeze_time('2017-06-02'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': payment.move_id.id,
                'datetime': fields.Datetime.from_string('2017-06-02 00:00:00'),
                'message': False,
                'state': 'payment_sent_pue',
                'sat_state': False,
                'cancel_button_needed': False,
                'retry_button_needed': False,
            },
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{'l10n_mx_edi_update_payments_needed': False}])

    def test_invoice_advanced_payment_flows(self):
        invoice = self._create_invoice(invoice_date_due='2017-01-01')
        self.assertRecordValues(invoice, [{'l10n_mx_edi_payment_policy': 'PUE'}])

        # Sign.
        with freeze_time('2017-01-07'), self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values = {
            'move_id': invoice.id,
            'datetime': fields.Datetime.from_string('2017-01-07 00:00:00'),
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])

        # Pay.
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'payment_date': '2017-06-01',
                'amount': 100.0,
            })\
            ._create_payments()
        with freeze_time('2017-06-02'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': payment.move_id.id,
                'datetime': fields.Datetime.from_string('2017-06-02 00:00:00'),
                'message': False,
                'state': 'payment_sent_pue',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': False,
            },
            sent_doc_values,
        ])

        # Force sending but force an error.
        with freeze_time('2017-06-03'), self.with_mocked_pac_sign_error():
            invoice.l10n_mx_edi_invoice_document_ids.sorted()[0].action_force_payment_cfdi()
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            {
                'move_id': payment.move_id.id,
                'datetime': fields.Datetime.from_string('2017-06-03 00:00:00'),
                'message': "turlututu",
                'state': 'payment_sent_failed',
                'sat_state': False,
                'cancellation_reason': False,
                'cancel_button_needed': False,
                'retry_button_needed': True,
            },
            sent_doc_values,
        ])

        # Retry.
        with freeze_time('2017-06-04'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_invoice_document_ids.sorted()[0].action_retry()
        payment_doc_values = {
            'move_id': payment.move_id.id,
            'datetime': fields.Datetime.from_string('2017-06-04 00:00:00'),
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment_doc_values,
            sent_doc_values,
        ])

        # Cancel the payment.
        with freeze_time('2017-08-01'), self.with_mocked_pac_cancel_error():
            payment.l10n_mx_edi_payment_document_ids.action_cancel()
        payment_doc_cancel_values = {
            'move_id': payment.move_id.id,
            'datetime': fields.Datetime.from_string('2017-08-01 00:00:00'),
            'message': "turlututu",
            'state': 'payment_cancel_failed',
            'sat_state': False,
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': True,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment_doc_cancel_values,
            payment_doc_values,
            sent_doc_values,
        ])

        # Retry.
        with freeze_time('2017-08-02'), self.with_mocked_pac_cancel_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        payment_doc_cancel_values.update({
            'datetime': fields.Datetime.from_string('2017-08-02 00:00:00'),
            'message': False,
            'state': 'payment_cancel',
            'sat_state': 'not_defined',
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': False,
        })
        payment_doc_values['sat_state'] = 'skip'
        payment_doc_values['cancel_button_needed'] = False
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment_doc_cancel_values,
            payment_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # New payment.
        payment2 = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})\
            ._create_payments()
        invoice.invalidate_recordset(fnames=['l10n_mx_edi_update_payments_needed'])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])
        with freeze_time('2017-08-03'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
            payment2.l10n_mx_edi_payment_document_ids.action_force_payment_cfdi()
        payment2_doc_values = {
            'move_id': payment2.move_id.id,
            'datetime': fields.Datetime.from_string('2017-08-03 00:00:00'),
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment2_doc_values,
            payment_doc_cancel_values,
            payment_doc_values,
            sent_doc_values,
        ])

        # Remove it and again a new payment.
        payment2.line_ids.remove_move_reconcile()
        payment3 = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})\
            ._create_payments()
        with freeze_time('2017-08-04'), self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
            payment3.l10n_mx_edi_payment_document_ids.action_force_payment_cfdi()
        payment3_doc_values = {
            'move_id': payment3.move_id.id,
            'datetime': fields.Datetime.from_string('2017-08-04 00:00:00'),
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
            'cancellation_reason': False,
            'cancel_button_needed': True,
            'retry_button_needed': False,
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment3_doc_values,
            payment2_doc_values,
            payment_doc_cancel_values,
            payment_doc_values,
            sent_doc_values,
        ])

        # Cancel payment2
        with freeze_time('2017-08-05'), self.with_mocked_pac_cancel_success():
            payment2.l10n_mx_edi_payment_document_ids.action_cancel()
        payment2_cancel_doc_values = {
            'move_id': payment2.move_id.id,
            'datetime': fields.Datetime.from_string('2017-08-05 00:00:00'),
            'message': False,
            'state': 'payment_cancel',
            'sat_state': 'not_defined',
            'cancellation_reason': '02',
            'cancel_button_needed': False,
            'retry_button_needed': False,
        }
        payment2_doc_values['sat_state'] = 'skip'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            payment2_cancel_doc_values,
            payment3_doc_values,
            payment2_doc_values,
            payment_doc_cancel_values,
            payment_doc_values,
            sent_doc_values,
        ])

    def test_payment_on_multiple_invoices(self):
        invoice1 = self._create_invoice_with_amount('2017-01-01', self.comp_curr, 1000.0)
        invoice2 = self._create_invoice_with_amount('2017-01-01', self.comp_curr, 1000.0)

        # Sign.
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice1._l10n_mx_edi_cfdi_invoice_try_send()
        inv1_sent_doc_values = {
            'move_id': invoice1.id,
            'invoice_ids': invoice1.ids,
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids, [inv1_sent_doc_values])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Create a payment with an higher amount than invoice1 and reconcile it.
        payment = self.env['account.payment'].create({
            'partner_id': self.partner_mx.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'date': invoice1.date,
            'amount': 1500.0,
            'currency_id': self.comp_curr.id,
        })
        payment.action_post()
        payment1_rec_line = payment.line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        invoice1_rec_line = invoice1.line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        (payment1_rec_line + invoice1_rec_line).reconcile()

        # Nothing change since the payment is not fully reconciled.
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids, [inv1_sent_doc_values])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Fully reconcile the payment.
        invoice2_rec_line = invoice2.line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        (payment1_rec_line + invoice2_rec_line).reconcile()
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Nothing change since invoice2 is not signed.
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids, [inv1_sent_doc_values])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Sign invoice2 and retry the payments.
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice2._l10n_mx_edi_cfdi_invoice_try_send()
        invoice1.invalidate_recordset(fnames=['l10n_mx_edi_update_payments_needed'])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()

        pay_sent_doc_values1 = {
            'move_id': payment.move_id.id,
            'invoice_ids': (invoice1 + invoice2).ids,
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv1_sent_doc_values,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        inv2_sent_doc_values = {
            'move_id': invoice2.id,
            'invoice_ids': invoice2.ids,
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice2.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv2_sent_doc_values,
        ])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Updating again the payment shouldn't do anything since the reconciliation hasn't changed.
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_error():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv1_sent_doc_values,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice2.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv2_sent_doc_values,
        ])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Change the reconciliation.
        invoice3 = self._create_invoice_with_amount('2017-01-01', self.comp_curr, 1000.0)
        invoice2_rec_line.remove_move_reconcile()
        invoice3_rec_line = invoice3.line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        (payment1_rec_line + invoice3_rec_line).reconcile()
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice3._l10n_mx_edi_cfdi_invoice_try_send()
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_error():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()
        pay_sent_doc_values2 = {
            'move_id': payment.move_id.id,
            'invoice_ids': (invoice1 + invoice3).ids,
            'message': "turlututu",
            'state': 'payment_sent_failed',
            'sat_state': False,
        }
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values2,
            pay_sent_doc_values1,
            inv1_sent_doc_values,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])
        self.assertRecordValues(invoice2.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv2_sent_doc_values,
        ])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        inv3_sent_doc_values = {
            'move_id': invoice3.id,
            'invoice_ids': invoice3.ids,
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice3.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values2,
            inv3_sent_doc_values,
        ])
        self.assertRecordValues(invoice3, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])

        # Change again the reconciliation.
        invoice4 = self._create_invoice_with_amount('2017-01-01', self.comp_curr, 1000.0)
        invoice1_rec_line.remove_move_reconcile()
        invoice4_rec_line = invoice4.line_ids.filtered(lambda x: x.account_type == 'asset_receivable')
        (payment1_rec_line + invoice4_rec_line).reconcile()
        with freeze_time('2017-01-01'), self.with_mocked_pac_sign_success():
            invoice4._l10n_mx_edi_cfdi_invoice_try_send()
        with freeze_time('2017-01-02'), self.with_mocked_pac_sign_success():
            invoice4.l10n_mx_edi_cfdi_invoice_try_update_payments()
        pay_sent_doc_values2.update({
            'invoice_ids': (invoice3 + invoice4).ids,
            'message': False,
            'state': 'payment_sent',
            'sat_state': 'not_defined',
        })
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv1_sent_doc_values,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice3.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values2,
            inv3_sent_doc_values,
        ])
        self.assertRecordValues(invoice3, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        inv4_sent_doc_values = {
            'datetime': fields.Datetime.from_string('2017-01-02 00:00:00'),
            'move_id': invoice4.id,
            'invoice_ids': invoice4.ids,
            'message': False,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice4.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values2,
            inv4_sent_doc_values,
        ])
        self.assertRecordValues(invoice4, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

        # Try to cancel the payment but it failed.
        self.assertRecordValues(payment.l10n_mx_edi_payment_document_ids.sorted(), [
            pay_sent_doc_values2,
            pay_sent_doc_values1,
        ])
        payment_doc = payment.l10n_mx_edi_payment_document_ids.sorted()[0]
        with freeze_time('2017-01-03'), self.with_mocked_pac_cancel_error():
            payment_doc.action_cancel()
        pay_cancel_doc_values = {
            'move_id': payment.move_id.id,
            'invoice_ids': (invoice3 + invoice4).ids,
            'message': "turlututu",
            'state': 'payment_cancel_failed',
            'sat_state': False,
        }
        self.assertRecordValues(payment.l10n_mx_edi_payment_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            pay_sent_doc_values1,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice3.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            inv3_sent_doc_values,
        ])
        self.assertRecordValues(invoice3, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])
        self.assertRecordValues(invoice4.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            inv4_sent_doc_values,
        ])
        self.assertRecordValues(invoice4, [{
            'l10n_mx_edi_update_payments_needed': True,
        }])

        # Change the reconciliation and successfully cancel.
        invoice3_rec_line.remove_move_reconcile()
        (payment1_rec_line + invoice1_rec_line).reconcile()
        payment_doc = payment.l10n_mx_edi_payment_document_ids.sorted()[0]
        with freeze_time('2017-01-03'), self.with_mocked_pac_cancel_success():
            payment_doc.action_retry()
        pay_cancel_doc_values.update({
            'invoice_ids': (invoice3 + invoice4).ids,
            'message': False,
            'state': 'payment_cancel',
            'sat_state': 'not_defined',
        })
        pay_sent_doc_values2['sat_state'] = 'skip'
        self.assertRecordValues(payment.l10n_mx_edi_payment_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            pay_sent_doc_values1,
        ])
        self.assertRecordValues(invoice1.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_sent_doc_values1,
            inv1_sent_doc_values,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice2, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice3.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            inv3_sent_doc_values,
        ])
        self.assertRecordValues(invoice3, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])
        self.assertRecordValues(invoice4.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_cancel_doc_values,
            pay_sent_doc_values2,
            inv4_sent_doc_values,
        ])
        self.assertRecordValues(invoice4, [{
            'l10n_mx_edi_update_payments_needed': False,
        }])

    @freeze_time('2017-01-01')
    def test_invoice_cancel_in_locked_period(self):
        invoice = self._create_invoice(invoice_date_due='2017-02-01')
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        payment = self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=invoice.ids) \
            .create({}) \
            ._create_payments()
        with self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(payment, [{'l10n_mx_edi_cfdi_state': 'sent'}])

        # Lock the period.
        invoice.company_id.fiscalyear_lock_date = '2017-01-01'

        # Cancel the invoice.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '03'}) \
                .action_cancel_invoice()
        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'cancel'}])

        # Cancel the payment.
        with self.with_mocked_pac_cancel_success():
            payment.l10n_mx_edi_payment_document_ids.action_cancel()
        self.assertRecordValues(payment, [{'l10n_mx_edi_cfdi_state': 'cancel'}])

    def test_invoice_payment_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case the invoice/payment is signed but the user manually cancel the document from the SAT portal (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        with freeze_time('2017-01-01'):
            invoice = self._create_invoice(invoice_date_due='2017-02-01')  # Force PPD
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                invoice.l10n_mx_edi_cfdi_try_sat()
            inv_sent_doc_values = {
                'move_id': invoice.id,
                'state': 'invoice_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [inv_sent_doc_values])
            self.assertRecordValues(invoice, [{
                'state': 'posted',
                'need_cancel_request': True,
                'show_reset_to_draft_button': False,
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'sent',
            }])

        # Register a payment and sign it.
        with freeze_time('2017-06-01'):
            payment = self.env['account.payment.register']\
                .with_context(active_model='account.move', active_ids=invoice.ids)\
                .create({'payment_date': '2017-06-01'})\
                ._create_payments()
            with self.with_mocked_pac_sign_success():
                invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()
            pay_sent_doc_values = {
                'move_id': payment.move_id.id,
                'state': 'payment_sent',
                'sat_state': 'valid',
            }
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                payment.move_id.l10n_mx_edi_cfdi_try_sat()
            self.assertRecordValues(payment.move_id.l10n_mx_edi_payment_document_ids, [pay_sent_doc_values])
            self.assertRecordValues(payment.move_id, [{
                'state': 'posted',
                'need_cancel_request': True,
                'show_reset_to_draft_button': False,
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'sent',
            }])

        # Manual cancellation from the SAT portal.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            invoice.l10n_mx_edi_cfdi_try_sat()

        inv_cancel_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_cancel',
            'sat_state': 'cancelled',
        }
        pay_cancel_doc_values = {
            'move_id': payment.move_id.id,
            'state': 'payment_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            pay_cancel_doc_values,
            inv_cancel_doc_values,
            pay_sent_doc_values,
            inv_sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'cancel',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])
        self.assertRecordValues(payment.move_id, [{
            'state': 'cancel',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])

    def test_global_invoice_production_sign_flow_cancel_from_the_sat(self):
        """ Test the case the global invoice is signed but the user manually cancel the document from the SAT portal (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        with freeze_time('2017-01-01'):
            invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
            with self.with_mocked_sat_call(lambda _x: 'valid'):
                invoice.l10n_mx_edi_cfdi_try_sat()
            sent_doc_values = {
                'invoice_ids': invoice.ids,
                'state': 'ginvoice_sent',
                'sat_state': 'valid',
            }
            self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])
            self.assertRecordValues(invoice, [{
                'l10n_mx_edi_update_sat_needed': True,
                'l10n_mx_edi_cfdi_sat_state': 'valid',
                'l10n_mx_edi_cfdi_state': 'global_sent',
            }])

        # Manual cancellation from the SAT portal.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            invoice.l10n_mx_edi_cfdi_try_sat()

        cancel_doc_values = {
            'invoice_ids': invoice.ids,
            'state': 'ginvoice_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'global_cancel',
        }])

    @freeze_time('2017-01-01')
    def test_invoice_production_sign_flow_cancel_from_odoo(self):
        """ Test the case the invoice is signed and the user request a cancellation in Odoo (production environment). """
        self.env.company.l10n_mx_edi_pac_test_env = False
        self.env.company.l10n_mx_edi_pac_username = 'test'
        self.env.company.l10n_mx_edi_pac_password = 'test'

        invoice = self._create_invoice(invoice_date_due='2017-02-01')  # Force PPD
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])

        # Approval of the sat.
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            invoice.l10n_mx_edi_cfdi_try_sat()
        sent_doc_values['sat_state'] = 'valid'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'valid',
            'l10n_mx_edi_cfdi_state': 'sent',
        }])

        # Request Cancel.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(invoice.button_request_cancel()['context'])\
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()
        cancel_request_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_cancel_requested',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_request_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'need_cancel_request': False,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'not_defined',
            'l10n_mx_edi_cfdi_state': 'cancel_requested',
        }])

        # The SAT rejected the cancellation.
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            invoice.l10n_mx_edi_cfdi_try_sat()
        cancel_request_doc_values['sat_state'] = 'valid'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_request_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'valid',
            'l10n_mx_edi_cfdi_state': 'sent',
        }])

        # Request Cancel again!
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(invoice.button_request_cancel()['context'])\
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()
        cancel_request_doc_values_2 = {
            'move_id': invoice.id,
            'state': 'invoice_cancel_requested',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_request_doc_values_2,
            cancel_request_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'need_cancel_request': False,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'not_defined',
            'l10n_mx_edi_cfdi_state': 'cancel_requested',
        }])

        # The SAT approved the cancellation.
        with self.with_mocked_sat_call(lambda _x: 'cancelled'):
            invoice.l10n_mx_edi_cfdi_try_sat()
        cancel_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_cancel',
            'sat_state': 'cancelled',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'cancel',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_update_sat_needed': False,
            'l10n_mx_edi_cfdi_sat_state': 'cancelled',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])

    @freeze_time('2017-01-01')
    def test_invoice_test_sign_flow_cancel_from_odoo(self):
        """ Test the case the invoice is signed and the user request a cancellation in Odoo (testing environment). """
        invoice = self._create_invoice(invoice_date_due='2017-02-01')  # Force PPD
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        sent_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_sent',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])

        # Approval of the sat.
        with self.with_mocked_sat_call(lambda _x: 'valid'):
            invoice.l10n_mx_edi_cfdi_try_sat()
        sent_doc_values['sat_state'] = 'valid'
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids, [sent_doc_values])
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'valid',
            'l10n_mx_edi_cfdi_state': 'sent',
        }])

        # Request Cancel.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(invoice.button_request_cancel()['context'])\
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()
        cancel_doc_values = {
            'move_id': invoice.id,
            'state': 'invoice_cancel',
            'sat_state': 'not_defined',
        }
        self.assertRecordValues(invoice.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values,
        ])
        self.assertRecordValues(invoice, [{
            'state': 'cancel',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_update_sat_needed': True,
            'l10n_mx_edi_cfdi_sat_state': 'not_defined',
            'l10n_mx_edi_cfdi_state': 'cancel',
        }])

    @freeze_time('2017-01-01')
    def test_payment_to_multiple_invoices_with_different_rfc(self):
        invoice1 = self._create_invoice(partner_id=self.partner_mx.id, invoice_date_due='2017-02-01')
        invoice2 = self._create_invoice(partner_id=self.partner_us.id, invoice_date_due='2017-02-01')

        with self.with_mocked_pac_sign_success():
            invoice1._l10n_mx_edi_cfdi_invoice_try_send()
            invoice2._l10n_mx_edi_cfdi_invoice_try_send()

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': sum((invoice1 + invoice2).mapped('amount_total')),
            'date': '2017-01-01',
        })
        payment.action_post()
        (invoice1 + invoice2 + payment.move_id).line_ids\
            .filtered(lambda x: x.account_type == 'asset_receivable')\
            .reconcile()

        with self.with_mocked_pac_sign_success():
            invoice1.l10n_mx_edi_cfdi_invoice_try_update_payments()
        self.assertRecordValues(payment.l10n_mx_edi_payment_document_ids.sorted(), [
            {
                'move_id': payment.move_id.id,
                'invoice_ids': (invoice1 + invoice2).ids,
                'message': "You can't register a payment for invoices having different RFCs.",
                'state': 'payment_sent_failed',
            },
        ])

    @freeze_time('2017-01-01')
    def test_invoice_to_public_flow(self):
        invoice = self._create_invoice(
            partner_id=self.partner_mx.id,
            l10n_mx_edi_cfdi_to_public=True,
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        self.assertRecordValues(invoice, [{'l10n_mx_edi_cfdi_state': 'sent'}])
        self.assertEqual(len(invoice.l10n_mx_edi_invoice_document_ids), 1)

        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({})\
            ._create_payments()
        with self.with_mocked_pac_sign_success():
            invoice.l10n_mx_edi_cfdi_invoice_try_update_payments()

        # We don't want to send 'Publico En General' payments.
        self.assertEqual(len(invoice.l10n_mx_edi_invoice_document_ids), 1)

    @freeze_time('2017-01-01')
    def test_invoice_cancellation_01(self):
        # Create and send the invoice.
        invoice = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'state': 'posted',
        }])

        # Create a replacement invoice.
        action_results = self.env['l10n_mx_edi.invoice.cancel'] \
            .with_context(invoice.button_request_cancel()['context']) \
            .create({}) \
            .action_create_replacement_invoice()
        new_invoice = self.env['account.move'].browse(action_results['res_id'])

        invoice.invalidate_recordset(fnames=['need_cancel_request', 'l10n_mx_edi_cfdi_cancel_id'])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': False,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_cfdi_cancel_id': new_invoice.id,
            'state': 'posted',
        }])
        self.assertRecordValues(new_invoice, [{
            'l10n_mx_edi_cfdi_state': False,
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': f'04|{invoice.l10n_mx_edi_cfdi_uuid}',
            'need_cancel_request': False,
            'show_reset_to_draft_button': False,
            'state': 'draft',
        }])

        # Sign the replacement invoice.
        new_invoice.action_post()
        with self.with_mocked_pac_sign_success():
            new_invoice._l10n_mx_edi_cfdi_invoice_try_send()

        invoice.invalidate_recordset(fnames=['need_cancel_request', 'l10n_mx_edi_cfdi_cancel_id'])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_cfdi_cancel_id': new_invoice.id,
            'state': 'posted',
        }])
        self.assertRecordValues(new_invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': f'04|{invoice.l10n_mx_edi_cfdi_uuid}',
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'state': 'posted',
        }])

        # Cancel the replacement invoice.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(new_invoice.button_request_cancel()['context'])\
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()

        invoice.invalidate_recordset(fnames=['need_cancel_request', 'l10n_mx_edi_cfdi_cancel_id'])
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'l10n_mx_edi_cfdi_cancel_id': new_invoice.id,
            'state': 'posted',
        }])
        self.assertRecordValues(new_invoice, [{
            'l10n_mx_edi_cfdi_state': 'cancel',
            'l10n_mx_edi_invoice_cancellation_reason': '02',
            'l10n_mx_edi_cfdi_origin': f'04|{invoice.l10n_mx_edi_cfdi_uuid}',
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'state': 'cancel',
        }])

        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(invoice.button_request_cancel()['context'])\
                .create({})\
                .action_cancel_invoice()
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'cancel',
            'l10n_mx_edi_invoice_cancellation_reason': '01',
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'l10n_mx_edi_cfdi_cancel_id': new_invoice.id,
            'state': 'cancel',
        }])

    @freeze_time('2017-01-01')
    def test_invoice_cancellation_02(self):
        invoice = self._create_invoice()
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()

        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'sent',
            'l10n_mx_edi_invoice_cancellation_reason': False,
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': True,
            'show_reset_to_draft_button': False,
            'state': 'posted',
        }])

        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()
        self.assertRecordValues(invoice, [{
            'l10n_mx_edi_cfdi_state': 'cancel',
            'l10n_mx_edi_invoice_cancellation_reason': '02',
            'l10n_mx_edi_cfdi_origin': False,
            'need_cancel_request': False,
            'show_reset_to_draft_button': True,
            'state': 'cancel',
        }])

    @freeze_time('2017-01-01')
    def test_global_invoice_cancellation_01(self):
        # Create and send the invoice.
        invoice1 = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        invoice2 = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        invoices = invoice1 + invoice2

        # Sign as a global invoice.
        with self.with_mocked_pac_sign_success():
            invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
        sent_doc_values1 = {
            'invoice_ids': invoices.ids,
            'state': 'ginvoice_sent',
            'attachment_uuid': invoices[0].l10n_mx_edi_cfdi_uuid,
            'attachment_origin': False,
            'cancellation_reason': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids, [sent_doc_values1])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_cfdi_state': 'global_sent',
            'l10n_mx_edi_cfdi_uuid': sent_doc_values1['attachment_uuid'],
        }])

        # Request a replacement for the global invoice.
        gi_doc1 = invoices.l10n_mx_edi_invoice_document_ids
        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc1.action_request_cancel()['context'])\
                .create({})\
                .action_create_replacement_invoice()
        sent_doc_values2 = {
            'invoice_ids': invoices.ids,
            'state': 'ginvoice_sent',
            'attachment_uuid': invoices[0].l10n_mx_edi_cfdi_uuid,
            'attachment_origin': f"04|{sent_doc_values1['attachment_uuid']}",
            'cancellation_reason': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values2,
            sent_doc_values1,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_cfdi_state': 'global_sent',
            'l10n_mx_edi_cfdi_uuid': sent_doc_values2['attachment_uuid'],
        }])

        # Cancel the first global invoice.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc1.action_request_cancel()['context'])\
                .create({})\
                .action_cancel_invoice()
        cancel_doc_values = {
            'invoice_ids': invoices.ids,
            'state': 'ginvoice_cancel',
            'attachment_uuid': sent_doc_values1['attachment_uuid'],
            'attachment_origin': False,
            'cancellation_reason': '01',
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values,
            sent_doc_values2,
            sent_doc_values1,
        ])
        self.assertRecordValues(invoice1, [{
            'l10n_mx_edi_cfdi_state': 'global_sent',
            'l10n_mx_edi_cfdi_uuid': sent_doc_values2['attachment_uuid'],
        }])

    @freeze_time('2017-01-01')
    def test_global_invoice_then_replacement_then_cancel_replacement_then_cancel_gi(self):
        invoice1 = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        invoice2 = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)
        invoices = invoice1 + invoice2

        # Failed to send the global invoice.
        with self.with_mocked_pac_sign_error():
            invoices._l10n_mx_edi_cfdi_global_invoice_try_send()
        sent_doc_values1 = {
            'move_id': None,
            'invoice_ids': invoices.ids,
            'message': "turlututu",
            'state': 'ginvoice_sent_failed',
            'sat_state': False,
            'attachment_uuid': False,
            'attachment_origin': False,
            'cancellation_reason': False,
            'retry_button_needed': True,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids, [sent_doc_values1])
        self.assertTrue(invoices.l10n_mx_edi_invoice_document_ids.attachment_id)

        # Successfully create the global invoice.
        with self.with_mocked_pac_sign_success():
            invoices.l10n_mx_edi_invoice_document_ids.action_retry()
        gi_attachment = invoices.l10n_mx_edi_cfdi_attachment_id
        self.assertEqual(len(gi_attachment), 1)
        sent_doc_values1.update({
            'message': False,
            'state': 'ginvoice_sent',
            'sat_state': 'not_defined',
            'attachment_id': gi_attachment.id,
            'attachment_uuid': invoices[0].l10n_mx_edi_cfdi_uuid,
            'attachment_origin': False,
            'retry_button_needed': False,
            'cancel_button_needed': True,
        })
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids, [sent_doc_values1])
        self.assertRecordValues(invoices, [{'l10n_mx_edi_update_sat_needed': True}] * 2)

        with self.with_mocked_sat_call(lambda _x: 'valid'):
            self.env['l10n_mx_edi.document']._fetch_and_update_sat_status(
                extra_domain=[('id', '=', invoices.l10n_mx_edi_invoice_document_ids.id)]
            )
        sent_doc_values1['sat_state'] = 'valid'
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids, [sent_doc_values1])

        # Request a replacement for the global invoice.
        gi_doc1 = invoices.l10n_mx_edi_invoice_document_ids
        with self.with_mocked_pac_sign_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc1.action_request_cancel()['context'])\
                .create({})\
                .action_create_replacement_invoice()

        gi_doc2 = invoices.l10n_mx_edi_invoice_document_ids.sorted()[0]
        self.assertTrue(gi_doc2.attachment_id)
        sent_doc_values2 = {
            'move_id': None,
            'invoice_ids': invoices.ids,
            'message': False,
            'state': 'ginvoice_sent',
            'sat_state': 'not_defined',
            'attachment_id': gi_doc2.attachment_id.id,
            'attachment_uuid': invoices[0].l10n_mx_edi_cfdi_uuid,
            'attachment_origin': f'04|{gi_doc1.attachment_uuid}',
            'cancellation_reason': False,
            'retry_button_needed': False,
            'cancel_button_needed': True,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values2,
            sent_doc_values1,
        ])

        # Request a replacement for the global invoice but it failed.
        with self.with_mocked_pac_sign_error():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc2.action_request_cancel()['context'])\
                .create({})\
                .action_create_replacement_invoice()

        gi_doc3 = invoices.l10n_mx_edi_invoice_document_ids.sorted()[0]
        self.assertTrue(gi_doc3.attachment_id)
        sent_doc_values3 = {
            'move_id': None,
            'invoice_ids': invoices.ids,
            'message': "turlututu",
            'state': 'ginvoice_sent_failed',
            'sat_state': False,
            'attachment_id': gi_doc3.attachment_id.id,
            'attachment_uuid': False,
            'attachment_origin': f'04|{gi_doc2.attachment_uuid}',
            'cancellation_reason': False,
            'retry_button_needed': True,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            sent_doc_values3,
            sent_doc_values2,
            sent_doc_values1,
        ])

        # Failed to cancel the second global invoice with cancellation reason 02.
        with self.with_mocked_pac_cancel_error():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc2.action_request_cancel()['context'])\
                .create({'cancellation_reason': '02'})\
                .action_cancel_invoice()
        cancel_doc_values1 = {
            'move_id': None,
            'invoice_ids': invoices.ids,
            'message': "turlututu",
            'state': 'ginvoice_cancel_failed',
            'sat_state': False,
            'attachment_id': gi_doc2.attachment_id.id,
            'attachment_uuid': gi_doc2.attachment_uuid,
            'attachment_origin': f'04|{gi_doc1.attachment_uuid}',
            'cancellation_reason': '02',
            'retry_button_needed': True,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values1,
            sent_doc_values2,
            sent_doc_values1,
        ])

        # Retry the cancellation of the second global invoice.
        with self.with_mocked_pac_cancel_success():
            invoices.l10n_mx_edi_invoice_document_ids.sorted()[0].action_retry()

        cancel_doc_values1.update({
            'message': False,
            'state': 'ginvoice_cancel',
            'sat_state': 'not_defined',
            'retry_button_needed': False,
            'cancel_button_needed': False,
        })
        sent_doc_values2['sat_state'] = 'skip'
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values1,
            sent_doc_values2,
            sent_doc_values1,
        ])

        # Successfully cancel the first global invoice.
        with self.with_mocked_pac_cancel_success():
            self.env['l10n_mx_edi.invoice.cancel']\
                .with_context(gi_doc1.action_request_cancel()['context'])\
                .create({})\
                .action_cancel_invoice()

        cancel_doc_values2 = {
            'move_id': None,
            'invoice_ids': invoices.ids,
            'message': False,
            'state': 'ginvoice_cancel',
            'sat_state': 'not_defined',
            'attachment_id': gi_doc1.attachment_id.id,
            'attachment_uuid': gi_doc1.attachment_uuid,
            'attachment_origin': False,
            'cancellation_reason': '01',
            'retry_button_needed': False,
            'cancel_button_needed': False,
        }
        self.assertRecordValues(invoices.l10n_mx_edi_invoice_document_ids.sorted(), [
            cancel_doc_values2,
            cancel_doc_values1,
            sent_doc_values2,
            sent_doc_values1,
        ])

    @freeze_time('2017-01-01')
    def test_global_invoice_after_failing_send_invoice(self):
        invoice = self._create_invoice(l10n_mx_edi_cfdi_to_public=True)

        with self.with_mocked_pac_sign_error():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertEqual(len(invoice.l10n_mx_edi_invoice_document_ids), 1)
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
        self.assertEqual(len(invoice.l10n_mx_edi_invoice_document_ids), 1)

    def test_invoice_cancellation_then_replacement_in_foreign_currency(self):
        date_1 = '2017-01-01'
        date_2 = '2017-01-02'
        self.setup_rates(self.usd, (date_1, 1 / 17.187), (date_2, 1 / 17.0357))

        with freeze_time(date_1):
            # create an invoice in USD when currency rate is 17.187
            invoice = self._create_invoice(
                invoice_date=date_1,
                date=date_1,
                currency_id=self.usd.id,
                invoice_line_ids=[
                    Command.create({
                        'product_id': self.product.id,
                        'price_unit': 100,
                        'quantity': 1,
                        'tax_ids': [Command.set(self.tax_16.ids)],
                    }),
                ],
            )
            with self.with_mocked_pac_sign_success():
                invoice._l10n_mx_edi_cfdi_invoice_try_send()

        self.assertRecordValues(invoice.line_ids, [
            {
                'amount_currency': -100.0,
                'balance': -1718.7,
                'debit': 0.0,
                'credit': 1718.7,
            },
            {
                'amount_currency': -16.0,
                'balance': -274.99,
                'debit': 0.0,
                'credit': 274.99,
            },
            {
                'amount_currency': 116.0,
                'balance': 1993.69,
                'debit': 1993.69,
                'credit': 0.0,
            },
        ])

        # create a replacement invoice when currency rate is 17.0357
        with freeze_time(date_2):
            action_results = self.env['l10n_mx_edi.invoice.cancel'] \
                .with_context(invoice.button_request_cancel()['context']) \
                .create({}) \
                .action_create_replacement_invoice()
            new_invoice = self.env['account.move'].browse(action_results['res_id'])

        # the amounts of the replacement invoice should use the current rate
        self.assertRecordValues(new_invoice.line_ids, [
            {
                'amount_currency': -100.0,
                'balance': -1703.57,
                'debit': 0.0,
                'credit': 1703.57,
                'tax_base_amount': 0.0,
            },
            {
                'amount_currency': -16.0,
                'balance': -272.57,
                'debit': 0.0,
                'credit': 272.57,
                'tax_base_amount': 1703.57,
            },
            {
                'amount_currency': 116.0,
                'balance': 1976.14,
                'debit': 1976.14,
                'credit': 0.0,
                'tax_base_amount': 0.0,
            },
        ])

    def test_cannot_delete_edi_document(self):
        invoice = self._create_invoice(invoice_date_due='2017-01-01')

        with freeze_time('2017-01-07'), self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_invoice_try_send()
        self.assertEqual(len(invoice.l10n_mx_edi_invoice_document_ids), 1)

        with self.assertRaises(UserError, msg="You can't unlink an attachment being an EDI document sent to the government."):
            invoice.l10n_mx_edi_invoice_document_ids.attachment_id.unlink()

    @freeze_time('2017-01-01 10:00:00')
    def test_global_invoice_year_month_format(self):
        """ Test that 'meses' and 'anno' are correctly set since we ignore them in
        other tests to allow to dynamically generate documents.
        """
        invoice = self._create_invoice(
            l10n_mx_edi_cfdi_to_public=True,
            invoice_line_ids=[
                Command.create({
                    'product_id': self.product.id,
                    'price_unit': 1000.0,
                    'tax_ids': [],
                }),
            ],
        )
        with self.with_mocked_pac_sign_success():
            invoice._l10n_mx_edi_cfdi_global_invoice_try_send()
        self._assert_global_invoice_cfdi_from_invoices(invoice, 'test_global_invoice_year_month_format')
