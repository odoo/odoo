from datetime import timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.models import Model
from odoo.tests import tagged
from odoo.tests.common import freeze_time
from odoo.tests.form import Form
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification.const import (
    PT_SIMPLIFIED_INVOICE_GOODS_LIMIT,
    PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT,
)
from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@freeze_time('2024-06-15')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtFlows(TestL10nPtCommon):

    # --------------------------------------------------
    # Section 1: Posting — Series assignment & validation
    # --------------------------------------------------

    def test_invoice_name_format(self):
        """ Invoice name should have a specific format """
        invoice = self.create_invoice('out_invoice', post=False)
        # removing all existing series and
        # assuming invoice has no series (if invoice has series then the name will be overridden
        # with the next sequence number of series after posting)
        self.env['l10n_pt.at.series'].with_context(active_test=False).search([]).unlink()
        invoice.l10n_pt_at_series_id = False
        self.assertFalse(invoice.name)
        invoice_form = Form(invoice)
        with self.assertRaisesRegex(ValidationError, "The document number .* is invalid."):
            invoice_form.name = 'INV 2024A/1.'     # Must have no symbols
        with self.assertRaisesRegex(ValidationError, "The document number .* is invalid."):
            invoice_form.name = 'INV 2024A'        # Must have slash at the end with sequence
        with self.assertRaisesRegex(ValidationError, "The document number .* is invalid."):
            invoice_form.name = 'INV/2024A/1'      # Must have a space after the prefix
        with self.assertRaisesRegex(ValidationError, "The document number .* is invalid."):
            invoice_form.name = 'INV 2024A/08/1'   # Must have a single slash only
        invoice_form.name = 'INV 2024A/1'
        invoice_form.save()
        self.assertEqual(invoice.name, 'INV 2024A/1')
        invoice.action_post()
        self.assertEqual(invoice.name, 'INV 2024A/00001')

    def test_cannot_post_before_previous_invoice_in_same_series(self):
        """ Invoices in same series must be in chronological ordering on invoice date """
        invoice = self.create_invoice('out_invoice', invoice_date=fields.Date.today())
        self.assertFalse(invoice.l10n_pt_show_future_date_warning)
        with self.assertRaisesRegex(UserError,
            "You cannot create an invoice with a date earlier than the date of the last invoice issued in this AT series"
        ):
            self.create_invoice('out_invoice', invoice_date=fields.Date.today() - timedelta(days=1))

        future_invoice = self.create_invoice('out_invoice', post=False, invoice_date=fields.Date.today() + timedelta(days=1))
        self.assertTrue(future_invoice.l10n_pt_show_future_date_warning)
        future_invoice.action_post()
        self.assertFalse(future_invoice.l10n_pt_show_future_date_warning)
        with self.assertRaisesRegex(UserError,
            "You cannot create an invoice with a date earlier than the date of the last invoice issued in this AT series"
        ):
            self.create_invoice('out_invoice', invoice_date=fields.Date.today())

        # Can create invoices on other series
        journal = self.env['account.journal'].create({
            'name': 'Another Sales Journal',
            'type': 'sale',
            'code': 'ASJ',
            'company_id': self.company_pt.id,
        })
        new_series = invoice.l10n_pt_at_series_id.copy({
            'journal_id': journal.id,
            'name': 'AnotherOne',
            'at_code': 'AT-AnotherOne',
        })
        invoice = self.create_invoice('out_invoice', post=False, invoice_date=fields.Date.today())
        invoice.l10n_pt_at_series_id = new_series
        invoice.action_post()
        self.assertEqual(invoice.l10n_pt_at_series_id, new_series)

    def test_cannot_reset_to_draft_and_change_series_on_posted_cancelled_invoice(self):
        """ Posted invoices cannot be set to draft and cannot change AT series value """
        regular_invoice = self.create_invoice('out_invoice')

        invoice_to_cancel = self.create_invoice('out_invoice')
        invoice_to_cancel.button_cancel()

        invoice_to_reverse = self.create_invoice('out_invoice')
        credit_note = invoice_to_reverse._reverse_moves()
        credit_note.action_post()

        test_series = regular_invoice.l10n_pt_at_series_id.copy({'name': 'COPY', 'at_code': 'AT-123141X'})

        invoice_to_expected_state = [
            (regular_invoice, 'posted'),
            (invoice_to_cancel, 'cancel'),
            (invoice_to_reverse, 'posted'),
            (credit_note, 'posted'),
        ]
        for invoice, expected_state in invoice_to_expected_state:
            self.assertEqual(invoice.state, expected_state)
            self.assertTrue(invoice.l10n_pt_at_series_id)
            self.assertTrue(invoice.l10n_pt_document_number)

            # Cannot set to draft
            self.assertFalse(invoice.show_reset_to_draft_button)
            with self.assertRaisesRegex(UserError, "You cannot reset to draft a Portuguese certified document with a document number"):
                invoice.button_draft()

            # Cannot change AT series value
            with self.assertRaisesRegex(UserError, "The AT Series of a posted document cannot be changed"):
                invoice.l10n_pt_at_series_id = test_series

    def test_series_posting_validation(self):
        """ Cannot post an invoice with
            1. no series
            2. series with different doc type
            3. series with date range outside invoice date
            4. inactive series
        """
        invoice = self.create_invoice('out_invoice', post=False)
        original_series = invoice.l10n_pt_at_series_id
        invoice.l10n_pt_at_series_id = False
        with patch('odoo.addons.l10n_pt_certification.models.account_move.AccountMove._l10n_pt_create_at_series_from_sequence', return_value=None), self.assertRaisesRegex(UserError, "Please select a series for this invoice"):
            invoice.action_post()

        invoice.l10n_pt_at_series_id = self.series_2024.filtered(lambda s: s.document_type != invoice.l10n_pt_document_type)[0]
        with self.assertRaisesRegex(UserError, "The series does not match the document type of the invoice"):
            invoice.action_post()

        early_series = self.env['l10n_pt.at.series'].create({
            'name': '2025FUTURE',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2025-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice',
            'prefix': 'FUT',
            'at_code': 'AT-TESTFUT2025',
        })
        self.assertTrue(early_series.active)
        invoice.l10n_pt_at_series_id = early_series
        with self.assertRaisesRegex(UserError, "An inactive series cannot be used"):
            invoice.action_post()

        inactive_series = self.series_2017.filtered(lambda s: s.document_type == invoice.l10n_pt_document_type)
        self.assertFalse(inactive_series.active)
        invoice.l10n_pt_at_series_id = self.series_2017.filtered(lambda s: s.document_type == invoice.l10n_pt_document_type)
        with self.assertRaisesRegex(UserError, "An inactive series cannot be used"):
            invoice.action_post()

        invoice.l10n_pt_at_series_id = original_series
        invoice.action_post()

    def test_series_posting_auto_creates_when_missing(self):
        """ An invoice with no series creates a new series from the invoice's sequence upon posting """
        journal = self.env['account.journal'].create({
            'name': 'Sales Journal Test',
            'type': 'sale',
            'code': 'SJT',
            'company_id': self.company_pt.id,
        })
        invoice = self.env['account.move'].with_company(self.company_pt).create({
            'name': 'INV 2024A/1',
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [self.tax_sale_23.id],
                }),
            ],
        })
        self.assertFalse(invoice.l10n_pt_at_series_id)
        self.assertFalse(invoice.l10n_pt_document_number)
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.name, 'INV 2024A/00001')
        self.assertEqual(invoice.l10n_pt_document_number, invoice.name)
        self.assertRecordValues(invoice.l10n_pt_at_series_id, [{
            'name': '2024A',
            'prefix': 'INV',
            'document_type': 'out_invoice',
            'date_start': fields.Date.from_string('2024-01-01'),
            'date_end': fields.Date.from_string('2024-12-31'),
        }])

    def test_series_posting_auto_receives_at_code_from_ws(self):
        """ When a series is created from posting an invoice, the series is communicated to AT portal via webserivce.
            which returns an AT (validation) code to be used on the series
        """
        journal = self.env['account.journal'].create({
            'name': 'Sales Journal AT',
            'type': 'sale',
            'code': 'SJAT',
            'company_id': self.company_pt.id,
        })
        invoice = self.env['account.move'].with_company(self.company_pt).create({
            'name': 'INV 2024A/1',
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [self.tax_sale_23.id],
                }),
            ],
        })
        # For WS communication, there needs to be a username set on the company
        self.company_pt.l10n_pt_at_ws_username = 'test'
        self.company_pt.l10n_pt_at_ws_password = 'test'
        with patch('odoo.addons.l10n_pt_certification.utils.series_ws.L10nPtAtSeriesWS.registar_serie', return_value='WS-CODE-123'):
            invoice.action_post()
        self.assertEqual(invoice.l10n_pt_at_series_id.at_code, 'WS-CODE-123')

    def test_series_posting_not_blocked_by_ws_failure(self):
        """ When a series is created from posting an invoice, the series is communicated to AT portal via webserivce.
            If the webservice communication is down or has an error, it shouldn't affect normal invoice posting.
            Invoice will not have an AT code which will block hashing until an AT validation code is obtained from the AT portal,
            either manually or using webservice again.
        """
        journal = self.env['account.journal'].create({
            'name': 'Sales Journal WSFail',
            'type': 'sale',
            'code': 'SJWF',
            'company_id': self.company_pt.id,
        })
        invoice = self.env['account.move'].with_company(self.company_pt).create({
            'name': 'INV 2024A/1',
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.today(),
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [self.tax_sale_23.id],
                }),
            ],
        })

        # For WS communication, there needs to be a username set on the company
        self.company_pt.l10n_pt_at_ws_username = 'test'
        self.company_pt.l10n_pt_at_ws_password = 'test'
        with mute_logger('odoo.addons.l10n_pt_certification.models.l10n_pt_at_series'), \
            patch('odoo.addons.l10n_pt_certification.utils.series_ws.L10nPtAtSeriesWS.registar_serie', side_effect=UserError("WS down")
        ):
            invoice.action_post()
        self.assertTrue(invoice.l10n_pt_at_series_id)
        self.assertFalse(invoice.l10n_pt_at_series_id.at_code)
        self.assertEqual(invoice.state, 'posted')

        # Cannot hash (to send or print) if the series doesn't have an AT validation code
        with self._mock_sign_records(), self.assertRaisesRegex(UserError, "The AT Series .* is missing the AT Validation Code."):
            invoice.button_hash()

    def test_series_recomputed(self):
        """ The series must be recomputed whe the following changes:
            1. document type
            2. invoice date
            3. journal id
        """
        out_invoice_series = self.series_2024.filtered(lambda s: s.document_type == 'out_invoice')

        # When document type changes
        inv_rec_series = self.env['l10n_pt.at.series'].create({
            'name': '2024',
            'company_id': self.company_pt.id,
            'training_series': True,
            'date_start': '2024-01-01',
            'journal_id': self.company_data['default_journal_sale'].id,
            'document_type': 'out_invoice_receipt',
            'prefix': 'INVREC',
            'at_code': 'AT-TESTFUT2025',
        })

        invoice = self.create_invoice('out_invoice', post=False)
        self.assertEqual(invoice.l10n_pt_at_series_id, out_invoice_series)
        self.assertEqual(invoice.l10n_pt_at_series_id.document_type, 'out_invoice')
        invoice.l10n_pt_document_type = 'debit_note'
        self.assertFalse(invoice.l10n_pt_at_series_id)
        invoice.l10n_pt_document_type = 'out_invoice_receipt'
        self.assertEqual(invoice.l10n_pt_at_series_id, inv_rec_series)
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_pt_document_type, 'out_invoice_receipt')
        self.assertEqual(invoice.l10n_pt_at_series_id, inv_rec_series)

        # When invoice date changes
        out_invoice_series.date_end = fields.Date.today()   # assume series has end date of today
        out_invoice_series_2 = out_invoice_series.copy({
            'name': 'Rest',
            'date_start': out_invoice_series.date_end + timedelta(days=1),
            'date_end': False,
            'at_code': 'AT-Rest',
        })
        invoice = self.create_invoice('out_invoice', invoice_date=fields.Date.today(), post=False)
        self.assertEqual(invoice.l10n_pt_at_series_id, out_invoice_series)
        invoice.invoice_date = fields.Date.today() + timedelta(days=1)
        self.assertEqual(invoice.l10n_pt_at_series_id, out_invoice_series_2)
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(invoice.l10n_pt_at_series_id, out_invoice_series_2)

        # When journal changes
        journal = self.env['account.journal'].create({
            'name': 'Another Sales Journal',
            'type': 'sale',
            'code': 'ASJ',
            'company_id': self.company_pt.id,
        })
        invoice = self.create_invoice('out_invoice', post=False)
        self.assertEqual(invoice.l10n_pt_at_series_id, out_invoice_series)
        invoice.journal_id = journal
        self.assertFalse(invoice.l10n_pt_at_series_id)

    # --------------------------------------------------
    # Section 2: Hash & signing (mocked IAP)
    # --------------------------------------------------

    def test_posted_and_canceled_invoices_in_hash_domain(self):
        """ Posted and cancelled invoices should be included in the hashing domain """
        domain = self.env['account.move'].with_company(self.company_pt)._get_move_hash_domain(force_hash=True)
        self.assertIn(('state', 'in', ['posted', 'cancel']), list(domain))

        regular_invoice = self.create_invoice('out_invoice')

        invoice_to_cancel = self.create_invoice('out_invoice')
        invoice_to_cancel.button_cancel()

        moves_to_hash = self.env['account.move'].search(domain).sorted('id')
        self.assertEqual(regular_invoice + invoice_to_cancel, moves_to_hash)

    def test_inalterable_hash_computed_correctly(self):
        invoice = self.create_invoice('out_invoice', do_hash=True, mock_hash=True, amount=200.0)
        self.assertIn('$1$', invoice.inalterable_hash)
        self.assertEqual(invoice.l10n_pt_inalterable_hash_version, 1)
        self.assertEqual(invoice.l10n_pt_inalterable_hash_short, 'AAAA')
        self.assertEqual(invoice.l10n_pt_atcud, 'AT-TESTINV2024-1')

    def test_atcud_not_computed_without_hash(self):
        invoice = self.create_invoice('out_invoice')
        self.assertEqual(invoice.l10n_pt_atcud, False)

    # --------------------------------------------------
    # Section 3: QR code (mocked hash)
    # --------------------------------------------------

    def test_cannot_create_qr_without_hash(self):
        """ Cannot create qr code without hash, valid PT VAT, or ATCUD """
        invoice = self.create_invoice('out_invoice')
        with self.assertRaisesRegex(UserError,
            r"Some fields required for the generation of the document are missing or invalid[\s\S]*The `hash` is not defined. You can contact the support.*"
        ):
            invoice.l10n_pt_verify_prerequisites_qr_code()

        self.company_pt.vat = ''
        invoice = self.create_invoice('out_invoice', do_hash=True, mock_hash=True)
        with self.assertRaisesRegex(UserError,
            r"Some fields required for the generation of the document are missing or invalid[\s\S]*The `VAT` of your company should be defined and match the following format: PT123456789.*"
        ):
            invoice.l10n_pt_verify_prerequisites_qr_code()
        self.company_pt.vat = 'PT123456789'

        invoice = self.create_invoice('out_invoice', do_hash=True, mock_hash=True)
        Model.write(invoice, {'l10n_pt_atcud': False})
        with self.assertRaisesRegex(UserError,
            r"Some fields required for the generation of the document are missing or invalid[\s\S]*The `ATCUD` is not defined. Please verify the AT series.*"
        ):
            invoice.flush_recordset()
            invoice.l10n_pt_verify_prerequisites_qr_code()

    def test_qr_code_computed_correctly(self):
        with self._mock_sign_records():
            invoice = self.create_invoice('out_invoice', do_hash=True, mock_hash=True)
        qr_str = invoice.l10n_pt_qr_code_str
        self.assertIn('A%3A', qr_str)
        self.assertIn('B%3A', qr_str)
        self.assertIn('C%3A', qr_str)
        self.assertIn('F%3A', qr_str)
        self.assertIn('G%3A', qr_str)
        self.assertIn('H%3A', qr_str)
        self.assertIn('N%3A', qr_str)
        self.assertIn('O%3A', qr_str)
        self.assertIn('Q%3A', qr_str)

    # --------------------------------------------------
    # Section 4: Print / Send / Preview
    # --------------------------------------------------

    def test_all_invoices_hashed_before_preview_send_print_and_reprint_reason(self):
        """ All existing invoices should be hashed when previewing, sending, or printing
            and sending/printing again should trigger reprint reason
        """
        def trigger_preview(invoice):
            invoice.preview_invoice()

        def trigger_send(invoice):
            # self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['email'])
            wizard = self.env['account.move.send.wizard'].create({
                'move_id': invoice.id,
            })
            return wizard.action_send_and_print()

        def trigger_print(invoice):
            invoice._get_invoice_legal_documents('pdf')

        def trigger_print_all(invoice):
            invoice._get_invoice_legal_documents_all()

        def trigger_reprinting(invoice):
            return invoice.action_print_pdf()

        test_cases = [
            ('Previewing', trigger_preview, None),
            ('Sending', trigger_send, trigger_send),
            ('Printing', trigger_print, trigger_reprinting),
            ('Printing all', trigger_print_all, trigger_reprinting),
        ]

        for action_name, trigger_action, retrigger_action in test_cases:
            with self.subTest(action=action_name):
                invoices = self.env['account.move']
                for _ in range(3):
                    invoices += self.create_invoice('out_invoice', do_hash=False, amount=100.0)
                self.assertFalse(any(invoices.mapped('inalterable_hash')))
                with self._mock_sign_records():
                    trigger_action(invoices[-1])
                self.assertTrue(all(invoices.mapped('inalterable_hash')))

                if retrigger_action:
                    action = retrigger_action(invoices[-1])
                    self.assertEqual(action['type'], 'ir.actions.act_window')
                    self.assertEqual(action['res_model'], 'l10n_pt.reprint.reason')

    def test_reprint_wizard_logs_reason_in_chatter(self):
        """ Make sure reprint reason is written in chatter """
        invoice = self.create_invoice('out_invoice')
        invoice.update_l10n_pt_print_version()
        invoice.update_l10n_pt_print_version()
        wizard = self.env['l10n_pt.reprint.reason'].with_context(
            active_model='account.move',
            active_ids=invoice.ids,
            action_to_return='action_print_pdf',
        ).create({'reason': 'Lost the original'})
        wizard.action_log_and_print()
        messages = invoice.message_ids.filtered(lambda m: m.body and 'Lost the original' in str(m.body))
        self.assertTrue(messages)

    # --------------------------------------------------
    # Section 5: Invoice-Receipts and Simplified-Invoices
    # --------------------------------------------------

    def test_invoice_receipt_type_when_paid_before_posting(self):
        """ If an invoice is paid before posting then it's considered an invoice receipt """
        # Draft -> Pay -> Post ==> Invoice-receipt
        invoice = self.create_invoice('out_invoice', amount=100.0, post=False)
        self.env['account.payment.register'].with_company(self.company_pt).with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': invoice.amount_total,
        }).action_create_payments()
        invoice.action_post()
        self.assertEqual(invoice.l10n_pt_document_type, 'out_invoice_receipt')

        invoice2 = self.create_invoice('out_invoice', amount=100.0, post=False)
        payment = self.env['account.payment'].with_company(self.company_pt).create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_a.id,
            'amount': invoice2.amount_total,
            'journal_id': self.company_data['default_journal_bank'].id,
            'invoice_ids': [(4, invoice2.id)],
        })
        payment.state = 'in_process'  # posts payment move, NO reconciliation
        invoice2.action_post()
        self.assertEqual(invoice2.l10n_pt_document_type, 'out_invoice_receipt')

        # Draft -> Post -> Pay ==> Regular Invoice
        invoice3 = self.create_invoice('out_invoice', amount=100.0)
        self.env['account.payment.register'].with_company(self.company_pt).with_context(
            active_model='account.move', active_ids=invoice3.ids,
        ).create({
            'journal_id': self.company_data['default_journal_bank'].id,
            'amount': invoice3.amount_total,
        }).action_create_payments()
        self.assertEqual(invoice3.l10n_pt_document_type, 'out_invoice')

    def test_sales_receipt_limits(self):
        """ A sales receipt's amount must be below a certain limit depending on if product is goods or service """
        good = self.product_a
        service = self.product_a.copy({'type': 'service'})

        with self.assertRaisesRegex(UserError, "A sales receipt.*cannot exceed.*EUR"):
            self.create_invoice('out_receipt', amount=PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT + 1, product_id=service.id)
        with self.assertRaisesRegex(UserError, "A sales receipt.*cannot exceed.*EUR"):
            self.create_invoice('out_receipt', amount=PT_SIMPLIFIED_INVOICE_GOODS_LIMIT + 1, product_id=good.id)

        receipt = self.create_invoice('out_receipt', amount=PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT + 1, product_id=good.id)
        self.assertEqual(receipt.state, 'posted')

        goods_service_receipt = self.create_invoice('out_receipt', post=False, amount=PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT / 2 + 2)
        goods_service_receipt.write({
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'product_id': service.id,
                    'quantity': 1,
                    'price_unit': PT_SIMPLIFIED_INVOICE_SERVICES_LIMIT / 2 - 1,
                    'tax_ids': [self.tax_sale_23.id],
                }),
            ],
        })
        with self.assertRaisesRegex(UserError, "A sales receipt .* cannot exceed .* EUR"):
            goods_service_receipt.action_post()

    # --------------------------------------------------
    # Section 6: Cancel & Reverse
    # --------------------------------------------------

    '''
        TODO
        Cancellation of invoices can only occur if all following conditions are met:
        - invoice is not sent to the customer (document not hashed)
        - there has no associated payments
        - no linked documents (like transport documents or credit notes)
        - not exported via SAF-T report
        If cancellation cannot occur, then invoice can reversed using a credit note
        Once invoice is cancelled, no other operation can be done on it

        Use case not handled:
        - cancelling credit notes
        - invoice -> reverse via credit note -> cancel credit note -> be able to reverse invoice again
    '''

    def test_cancel_fully_reversed_or_cancelled_invoice_blocked(self):
        """ Cannot cancel an already reversed invoice or cancelled invoice """
        invoice = self.create_invoice('out_invoice', product_id=self.product_a.id)
        credit_note = invoice._reverse_moves()
        credit_note.action_post()
        with self.assertRaisesRegex(UserError, "You cannot cancel an invoice that has already been fully reversed or cancelled."):
            invoice.button_cancel()

        invoice2 = self.create_invoice('out_invoice', product_id=self.product_a.id)
        invoice2.button_cancel()
        with self.assertRaisesRegex(UserError, "You cannot cancel an invoice that has already been fully reversed or cancelled."):
            invoice2.button_cancel()

    def test_reverse_fully_reversed_or_cancelled_invoice_blocked(self):
        """ Cannot reverse an already reversed invoice or cancelled invoice """
        invoice = self.create_invoice('out_invoice', product_id=self.product_a.id)
        credit_note = invoice._reverse_moves()
        credit_note.action_post()
        with self.assertRaisesRegex(UserError, "You cannot reverse an invoice that has already been fully reversed or cancelled."):
            invoice.action_reverse()

        invoice2 = self.create_invoice('out_invoice', product_id=self.product_a.id)
        invoice2.button_cancel()
        with self.assertRaisesRegex(UserError, "You cannot reverse an invoice that has already been fully reversed or cancelled."):
            invoice2.action_reverse()

    def test_refunds_contain_reference_to_original_document(self):
        """ Credit notes must reference an original invoice """
        manual_credit_note = self.create_invoice('out_refund', post=False)
        self.assertFalse(manual_credit_note.reversed_entry_id)
        with self.assertRaisesRegex(UserError, "You cannot post a credit note without referencing the original invoice."):
            manual_credit_note.action_post()

        invoice = self.create_invoice('out_invoice', product_id=self.product_a.id)
        self.assertTrue(invoice._refunds_origin_required())
        credit_note = invoice._reverse_moves()
        self.assertEqual(credit_note.reversed_entry_id, invoice)
        self.assertEqual(invoice.reversal_move_ids, credit_note)
        credit_note.action_post()
        self.assertEqual(credit_note.reversed_entry_id, invoice)
        self.assertEqual(invoice.reversal_move_ids, credit_note)

    def test_credit_note_requires_reason(self):
        """ Credit notes issued must specify a reason """
        invoice = self.create_invoice('out_invoice', product_id=self.product_a.id)
        reversal_wizard = self.env['account.move.reversal'].with_company(self.company_pt).with_context(
            active_model='account.move', active_ids=invoice.ids,
        ).create({
            'journal_id': self.company_data['default_journal_sale'].id,
        })
        with self.assertRaisesRegex(UserError, "For Credit Notes issued in Portugal, you need to specify a Reason."):
            reversal_wizard.reverse_moves()

    def test_credit_note_quantity_amount_cannot_exceed_original(self):
        """ The sum of quantities and amounts for all credit notes issued for an invoice cannot exceed the original invoice values """
        invoice = self.create_invoice('out_invoice', product_id=self.product_a.id, amount=1000.0, quantity=5)
        credit_note = invoice._reverse_moves()
        self.assertEqual(credit_note.invoice_line_ids.quantity, 5)
        self.assertEqual(credit_note.invoice_line_ids.price_unit, 1000)

        credit_note.invoice_line_ids.quantity = 10
        with self.assertRaisesRegex(UserError, "This credit note has items of a quantity exceeding that of the original"):
            credit_note.action_post()

        credit_note.invoice_line_ids.quantity = 5
        credit_note.invoice_line_ids.price_unit = 5000
        with self.assertRaisesRegex(UserError, "This credit note exceeds the amount of the original customer invoice"):
            credit_note.action_post()

        credit_note.invoice_line_ids.quantity = 2
        credit_note.invoice_line_ids.price_unit = 500.0
        credit_note.action_post()
        self.assertNotEqual(invoice.payment_state, 'reversed')
        # Partially refunded -> q=2 , price=500 -> total=1000
        # Remaining to be refunded -> q=3 , total=4000

        credit_note_2 = invoice._reverse_moves()
        self.assertEqual(credit_note_2.invoice_line_ids.quantity, 5)
        self.assertEqual(credit_note_2.invoice_line_ids.price_unit, 1000)
        credit_note_2.invoice_line_ids.quantity = 4
        # Credit note quantity = 4 > 3 = the remaining quantity
        # Even though the total amount = 4 * 1000 = 4000 satisfies the remaining total amount
        with self.assertRaisesRegex(UserError, "This credit note in conjunction with.*has items of a quantity exceeding that of the original customer invoice"):
            credit_note_2.action_post()

        credit_note_2.invoice_line_ids.quantity = 3
        credit_note_2.invoice_line_ids.price_unit = 1500.0
        # Credit note total = 3 * 1500 = 4500 > 4000 = the remaining total
        with self.assertRaisesRegex(UserError, "This credit note in conjunction with.*exceeds the amount on the original customer invoice"):
            credit_note_2.action_post()

        credit_note_2.invoice_line_ids.quantity = 2
        credit_note_2.invoice_line_ids.price_unit = 2000.0
        # Credit note total = 2 * 2000 = 4000 = the whole remaining total
        credit_note_2.action_post()
        # The invoice now is fully reversed (note: amount fully refunded but quantities not fully refunded)
        self.assertEqual(invoice.payment_state, 'reversed')

    # --------------------------------------------------
    # Section 7: Taxes and Discounts
    # --------------------------------------------------

    def test_posting_without_taxes_on_lines_raises(self):
        """ All invoice lines must contain taxes """
        invoice = self.create_invoice('out_invoice', post=False)
        invoice.write({
            'line_ids': [
                Command.create({
                    'name': 'Product A',
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [],
                }),
            ],
        })
        with self.assertRaisesRegex(ValidationError, "You cannot create an invoice line without VAT tax"):
            invoice.action_post()

    def test_global_and_line_discount(self):
        """ The global discount is used to adjust the values of the line discount """
        invoice = self.create_invoice('out_invoice', post=False, product_id=self.product_a.id, amount=1000.0)

        with self.assertRaisesRegex(ValidationError, "Discount amounts should be between 0% and 100%"):
            invoice.l10n_pt_global_discount = -1.0

        invoice.l10n_pt_global_discount = 10.0
        self.assertAlmostEqual(invoice.invoice_line_ids.discount, 10.0)
        self.assertAlmostEqual(invoice.invoice_line_ids.price_subtotal, 900.0)

        with self.assertRaisesRegex(ValidationError, "Discount amounts should be between 0% and 100%"):
            invoice.invoice_line_ids.l10n_pt_line_discount = -1.0

        invoice.invoice_line_ids.l10n_pt_line_discount = 10.0
        self.assertAlmostEqual(invoice.invoice_line_ids.discount, 19.0)
        self.assertAlmostEqual(invoice.invoice_line_ids.price_subtotal, 810.0)
