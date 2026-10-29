import re
import unittest
from datetime import date, datetime
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.sql_db import Cursor
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon
from odoo.addons.l10n_pt_certification.utils.hashing import L10nPtSigningUnavailable


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtInvoicing(TestL10nPtCommon):
    """
    The life of a PT document, from its number to its corrections and its receipt.

    Posting a PT invoice takes the next number of its AT series, as its name; issuing it, later,
    makes that number its document number (Despacho 8632/2014 1.6, 2.2.1; FAQ R23). A series has no
    gap, follows the documents' dates, and is validated by the AT before use (Portaria 195/2020).

    A PT invoice is issued -- given its document number, ATCUD and signature -- when it is first
    generated for the customer, not when it is posted (FAQ R23; Despacho 8632/2014 2.1.1): printed,
    previewed, downloaded, sent, or annulled. The invoices of a series are issued in number order.
    Online payments, the PoS and down payments issue through `l10n_pt_issue_automatically`, tested in
    `l10n_pt_sale` and `l10n_pt_pos`.

    An issued invoice is never changed or deleted: it is corrected by a credit or debit note that
    references it and gives a reason, or annulled (Despacho 8632/2014 3.3.8; Portaria 302/2016
    4.1.4.19.5). Each is a document of its own series.

    A payment received by a PT company is a receipt (RG): numbered in an RG series when posted, in
    date order, referencing issued invoices, exported with its payment mechanism (Portaria 302/2016
    4.4). Payments made by the company are not PT documents.
    """

    # -------------------------------------------------------------------------
    # Numbering
    # -------------------------------------------------------------------------

    def test_first_documents_of_series_as_billing_user(self):
        """
        Whoever issues the first document of a series creates the series' number sequence: a user
        with billing rights only does so for an invoice, a credit note and a receipt (PT-121).
        """
        invoices = self.post((self.make_invoice() + self.make_invoice()).with_user(self.billing_user))
        self.assertEqual(invoices.mapped('name'), ['FT 2026/00001', 'FT 2026/00002'])
        self.issue(invoices)
        credit_note = self.issue(self.post(self.reverse(invoices[0])))
        self.assertEqual(credit_note.l10n_pt_document_number, 'NC 2026/00001')
        receipt = self.make_receipt(invoices[1])
        self.assertEqual(receipt.l10n_pt_document_number, 'RG 2026/00001')
        self.assertIssued(invoices + credit_note)
        self.assertIssued(receipt)
        self.assertFalse(invoices.env.su or credit_note.env.su or receipt.env.su)
        for series in self.series_ft + self.series_nc + self.series_rg:
            self.assertEqual(self.env['ir.sequence'].search_count([
                ('code', '=', f'l10n_pt_certification.{series.document_type}_2026_sequence'),
                ('company_id', '=', self.company_pt.id),
            ]), 1)

    def test_name_format(self):
        """A PT document number reads `<type code> <series>/<number>` (Despacho 8632/2014 2.2.1)."""
        invoice = self.make_invoice()
        for name in ('FT 2026A/1.', 'FT 2026A', 'FT/2026A/1', 'FT 2026A/08/1'):
            with self.subTest(name=name), self.assertRaisesRegex(ValidationError, "The document number .* is invalid"):
                invoice.name = name
                invoice._onchange_l10n_pt_name()
        invoice.name = 'FT 2026A/1'
        invoice._onchange_l10n_pt_name()

    def test_posting_numbers_without_issuing(self):
        """Posting gives the invoice its number in its series as its name, not a document number, ATCUD or signature (PT-105)."""
        invoice = self.post(self.make_invoice().with_user(self.billing_user))
        self.assertRecordValues(invoice, [{
            'state': 'posted',
            'name': 'FT 2026/00001',
            'l10n_pt_document_type': 'out_invoice',
            'l10n_pt_at_series_id': self.series_ft.id,
        }])
        self.assertNotIssued(invoice)
        self.assertFalse(self.signing.calls)

    def test_document_types(self):
        """Each document type is numbered in a series of its own type: FT, FS, FR, NC."""
        invoice = self.post(self.make_invoice())
        simplified = self.post(self.make_invoice('out_receipt', partner=False))
        credit_note = self.post(self.reverse(self.issue(invoice)))
        self.assertRecordValues(invoice + simplified + credit_note, [
            {'name': 'FT 2026/00001', 'l10n_pt_document_type': 'out_invoice', 'l10n_pt_at_series_id': self.series_ft.id},
            {'name': 'FS 2026/00001', 'l10n_pt_document_type': 'out_receipt', 'l10n_pt_at_series_id': self.series_fs.id},
            {'name': 'NC 2026/00001', 'l10n_pt_document_type': 'out_refund', 'l10n_pt_at_series_id': self.series_nc.id},
        ])
        vendor_bill = self.post(self.make_invoice('in_invoice', lines=[{'tax_ids': self.tax_purchase_a}]))
        self.assertFalse(vendor_bill.l10n_pt_at_series_id)
        self.assertFalse(vendor_bill.l10n_pt_document_type)

    def test_invoice_paid_before_posting_is_invoice_receipt(self):
        """An invoice fully paid before it is posted is an invoice-receipt (FR), in an FR series."""
        invoice = self.make_invoice()
        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_pt.id,
            'amount': invoice.amount_total,
            'journal_id': self.company_data['default_journal_bank'].id,
            'invoice_ids': [Command.link(invoice.id)],
        })
        # As an online payment leaves it: processed, before the invoice exists for the customer.
        payment.state = 'in_process'
        self.post(invoice)
        self.assertRecordValues(invoice, [{
            'name': 'FR 2026/00001',
            'l10n_pt_document_type': 'out_invoice_receipt',
            'l10n_pt_at_series_id': self.series_fr.id,
        }])
        paid_after = self.post(self.make_invoice())
        self.make_receipt(self.issue(paid_after))
        self.assertEqual(paid_after.l10n_pt_document_type, 'out_invoice')

    def test_debit_note(self):
        """A debit note is numbered in an ND series."""
        if 'debit_origin_id' not in self.env['account.move']._fields:
            self.skipTest("account_debit_note is not installed")
        invoice = self.issue(self.post(self.make_invoice()))
        debit_note = self.post(self.make_invoice(debit_origin_id=invoice.id))
        self.assertRecordValues(debit_note, [{'name': 'ND 2026/00001', 'l10n_pt_at_series_id': self.series_nd.id}])

    def test_series_selection(self):
        """
        The series of an invoice is the active series of its journal and type valid on its date: never a
        series of another type (PT-14), nor an ended one or one not covering the date.
        """
        receipt = self.make_invoice('out_receipt')
        self.assertEqual(receipt.l10n_pt_at_series_id, self.series_fs)
        receipt.move_type = 'out_invoice'
        self.assertEqual(receipt.l10n_pt_at_series_id, self.series_ft)

        self.series_ft.date_end = date(2026, 6, 14)
        series_ft_b = self.series_factory(name='2026B', date_start='2026-06-15')
        self.env.invalidate_all()
        self.assertEqual(self.post(self.make_invoice()).l10n_pt_at_series_id, series_ft_b)

        next_year = self.make_invoice(invoice_date=date(2027, 1, 4))
        self.assertFalse(next_year.l10n_pt_at_series_id)
        other_journal = self.company_data['default_journal_sale'].copy({'code': 'SJ2'})
        self.assertFalse(self.make_invoice(journal_id=other_journal.id).l10n_pt_at_series_id)

    def test_series_follows_draft_changes(self):
        """
        A draft's series follows its date and journal as they change: it moves to the series valid
        on the new date, or of the new journal, and is cleared when there is none. Posting checks the
        series' type and dates, not its journal: a series left behind would number the invoice in
        another journal's series.
        """
        self.series_ft.date_end = date(2026, 6, 20)
        series_ft_b = self.series_factory(name='2026B', date_start='2026-06-21')
        other_journal = self.company_data['default_journal_sale'].copy({'code': 'SJ2'})
        other_series = self.series_factory(name='2026J', journal_id=other_journal.id)
        invoice = self.make_invoice()
        self.assertEqual(invoice.l10n_pt_at_series_id, self.series_ft)
        for vals, series in (
            ({'invoice_date': date(2026, 6, 21)}, series_ft_b),
            ({'invoice_date': date(2027, 1, 4)}, self.env['l10n_pt.at.series']),
            ({'invoice_date': date(2026, 6, 15)}, self.series_ft),
            ({'journal_id': other_journal.id}, other_series),
            ({'journal_id': self.company_data['default_journal_sale'].id}, self.series_ft),
        ):
            with self.subTest(vals=vals):
                invoice.write(vals)
                self.assertEqual(invoice.l10n_pt_at_series_id, series)
        self.assertEqual(self.post(invoice).name, 'FT 2026/00001')

    def test_series_validity_checked_at_posting(self):
        """A series chosen by hand is refused at posting if of another type, ended, or not yet started."""
        future_series = self.series_factory(name='2027', date_start='2027-01-01', date_end=False)
        ended_series = self.series_factory(name='2025', date_start='2025-01-01', date_end='2025-12-31')
        invoice = self.make_invoice()
        for series, message in (
            (self.series_fs, "The series does not match the document type"),
            (future_series, "An inactive series cannot be used"),
            (ended_series, "An inactive series cannot be used"),
        ):
            with self.subTest(series=series.document_identifier):
                invoice.l10n_pt_at_series_id = series
                with self.assertRaisesRegex(UserError, message):
                    self.post(invoice)
        invoice.l10n_pt_at_series_id = self.series_ft
        self.assertEqual(self.post(invoice).name, 'FT 2026/00001')

    def test_missing_series_offers_prefilled_series(self):
        """
        Without a series, posting is refused and offers the series form prefilled from the invoice's
        sequence, under a name no other series of the company holds (PT-122); nothing is created.
        Saved as proposed, with its AT code, the series numbers the invoice.
        """
        journal = self.env['account.journal'].create({'name': 'Vendas Loja', 'type': 'sale', 'code': 'LOJA'})
        invoice = self.make_invoice(journal_id=journal.id)
        series_count = self.env['l10n_pt.at.series'].search_count([])
        with self.assertRaisesRegex(RedirectWarning, "There is no AT series for") as cm:
            self.post(invoice)
        self.assertEqual(invoice.state, 'draft')
        self.assertEqual(self.env['l10n_pt.at.series'].search_count([]), series_count)
        action = cm.exception.args[1]
        self.assertEqual(action['res_model'], 'l10n_pt.at.series')
        self.assertEqual({key: value for key, value in action['context'].items() if key.startswith('default_')}, {
            'default_name': 'LOJA2026',
            'default_prefix': 'LOJA',
            'default_document_type': 'out_invoice',
            'default_journal_id': journal.id,
            'default_company_id': self.company_pt.id,
            'default_date_start': '2026-01-01',
            'default_date_end': '2026-12-31',
        })
        # `2026` is FT 2026's, of the default journal: the journal's code makes the name unique.
        series = self.env['l10n_pt.at.series'].with_context(action['context']).create({'at_code': 'ATLOJA2026'})
        self.issue(self.post(invoice))
        self.assertEqual(invoice.l10n_pt_at_series_id, series)
        self.assertEqual(invoice.l10n_pt_atcud, 'ATLOJA2026-1')

    def test_typed_name_proposes_series_then_renumbered(self):
        """
        The number typed on a draft without series names the series proposed at posting; once that
        series exists, posting numbers the invoice in it, in the series' own format.
        """
        journal = self.env['account.journal'].create({'name': 'Vendas Loja', 'type': 'sale', 'code': 'LOJA'})
        invoice = self.make_invoice(journal_id=journal.id)
        invoice.name = 'FT 2026A/1'
        with self.assertRaisesRegex(RedirectWarning, "There is no AT series for") as cm:
            self.post(invoice)
        context = cm.exception.args[1]['context']
        self.assertEqual((context['default_prefix'], context['default_name']), ('FT', '2026A'))
        series = self.env['l10n_pt.at.series'].with_context(context).create({'at_code': 'ATFT2026A'})
        self.post(invoice)
        self.assertRecordValues(invoice, [{'name': 'FT 2026A/00001', 'l10n_pt_at_series_id': series.id}])

    def test_series_without_at_code_refused(self):
        """No document is numbered in a series before the AT validated it; no number is consumed (PT-22)."""
        self.series_ft.at_code = False
        invoice = self.make_invoice()
        with self.assertRaisesRegex(RedirectWarning, "has no AT validation code yet"):
            self.post(invoice)
        self.assertEqual(invoice.state, 'draft')
        self.series_ft.at_code = 'ATLATECODE'
        self.issue(self.post(invoice))
        self.assertEqual(invoice.name, 'FT 2026/00001')
        self.assertEqual(invoice.l10n_pt_atcud, 'ATLATECODE-1')

    def test_chronology(self):
        """
        No invoice is dated before the last one of its series; once a future-dated one is issued, the
        series waits for its date. Other series are not concerned (Despacho 8632/2014 2.2.2).
        """
        future = self.make_invoice(invoice_date=date(2026, 6, 20))
        self.assertTrue(future.l10n_pt_show_future_date_warning)
        self.post(future)
        self.assertFalse(future.l10n_pt_show_future_date_warning)
        with self.assertRaisesRegex(UserError, "dated earlier than the last document issued in this AT series"):
            self.post(self.make_invoice())
        self.post(self.make_invoice('out_receipt'))
        self.assertEqual(self.post(self.make_invoice(invoice_date=date(2026, 6, 20))).name, 'FT 2026/00002')

    def test_reset_to_draft_keeps_number(self):
        """
        An invoice reset to draft before it is issued keeps its number, series and type; posted again,
        its date must stay between its neighbours'. An issued invoice cannot be reset.
        """
        invoices = self.post(
            self.make_invoice(invoice_date=date(2026, 6, 10))
            + self.make_invoice(invoice_date=date(2026, 6, 12))
            + self.make_invoice(invoice_date=date(2026, 6, 14))
        )
        middle = invoices[1]
        middle.button_draft()
        self.assertRecordValues(middle, [{
            'state': 'draft', 'name': 'FT 2026/00002', 'l10n_pt_at_series_id': self.series_ft.id,
            'l10n_pt_document_type': 'out_invoice',
        }])
        with self.assertRaisesRegex(UserError, "The AT Series of a posted document cannot be changed"):
            middle.l10n_pt_at_series_id = self.series_factory(name='2026B')
        middle.invoice_date = date(2026, 6, 15)
        with self.assertRaisesRegex(UserError, "its date must stay between those of the invoices numbered right before and after it"):
            self.post(middle)
        middle.invoice_date = date(2026, 6, 13)
        self.post(middle)
        self.assertEqual(middle.name, 'FT 2026/00002')

        self.issue(invoices[0])
        self.assertFalse(invoices[0].show_reset_to_draft_button)
        with self.assertRaisesRegex(UserError, "You cannot reset to draft a Portuguese certified document"):
            invoices[0].button_draft()

    def test_clock_behind_last_issued_document(self):
        """
        A system clock earlier than the last document issued, of any type, is to be confirmed before
        issuing; confirming holds until a later document is issued (Despacho 8632/2014 3.4.3, PT-68).
        """
        with freeze_time('2026-06-15 11:00:00'):
            self.issue(self.post(self.make_invoice('out_receipt')))
        invoice = self.make_invoice().with_user(self.billing_user)
        with self.assertRaisesRegex(RedirectWarning, "earlier than those of the last document issued"):
            self.post(invoice)
        self.assertEqual(invoice.state, 'draft')
        self.env['res.company'].with_user(self.billing_user)._l10n_pt_confirm_system_clock()
        self.issue(self.post(invoice))
        self.issue(self.post(self.make_invoice()))
        self.assertIssued(invoice)

    def test_line_rules(self):
        """
        Every priced line has a product and one VAT tax, withholding aside; sections and notes are free;
        no customer line is zero or negative, while vendor bills may have such lines (PT-92).
        """
        withholding = self.env['account.tax'].create({
            'name': 'Retenção IRS 25%', 'amount': -25.0, 'type_tax_use': 'sale', 'company_id': self.company_pt.id,
        })
        for lines, error, message in (
            ([{'tax_ids': self.env['account.tax']}], ValidationError, "without VAT tax"),
            ([{'tax_ids': self.tax_sale_23 + self.tax_sale_exempt}], ValidationError, "can only carry one tax"),
            ([{'product_id': False, 'name': 'Serviço'}], UserError, "needs a product"),
            ([{'price_unit': 0.0}], ValidationError, "amount of 0 are not allowed"),
            ([{'price_unit': -10.0}], ValidationError, "negative lines"),
        ):
            # A refused line rolls back to the savepoint, or its rows would fail every later check.
            with self.subTest(message=message), self.assertRaisesRegex(error, message), self.env.cr.savepoint():
                self.post(self.make_invoice(lines=lines))
        invoice = self.post(self.make_invoice(lines=[
            {'tax_ids': self.tax_sale_23 + withholding},
            {'display_type': 'line_section', 'name': 'Secção', 'product_id': False, 'tax_ids': self.env['account.tax']},
            {'display_type': 'line_note', 'name': 'Nota', 'product_id': False, 'tax_ids': self.env['account.tax']},
        ]))
        self.assertEqual(invoice.state, 'posted')
        bill = self.post(self.make_invoice('in_invoice', lines=[
            {'tax_ids': self.tax_purchase_a},
            {'price_unit': -10.0, 'tax_ids': self.tax_purchase_a},
            {'price_unit': 0.0, 'tax_ids': self.tax_purchase_a},
        ]))
        self.assertEqual(bill.state, 'posted')

    def test_tax_without_exemption_reason_refused(self):
        """A tax charging nothing needs an exemption reason, also one stored before that rule (Despacho 8632/2014 3.2.6)."""
        self.tamper(self.tax_sale_exempt, 'l10n_pt_tax_exemption_reason', None)
        invoice = self.make_invoice(lines=[{'tax_ids': self.tax_sale_exempt}])
        self.assertIn(self.tax_sale_exempt.name, invoice.l10n_pt_saft_missing_data)
        with self.assertRaisesRegex(ValidationError, "needs a VAT exemption reason"):
            self.post(invoice)

    def test_simplified_invoice_limits(self):
        """A simplified invoice (FS) is limited to 1000 EUR for goods, 100 EUR with services, converted to EUR (CIVA 40(1))."""
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 2.0)])
        exempt = {'tax_ids': self.tax_sale_exempt}
        for lines, currency, allowed in (
            ([{**exempt, 'price_unit': 1000.0}], None, True),
            ([{**exempt, 'price_unit': 1000.01}], None, False),
            ([{**exempt, 'price_unit': 100.0, 'product_id': self.product_service}], None, True),
            ([{**exempt, 'price_unit': 100.01, 'product_id': self.product_service}], None, False),
            ([{**exempt, 'price_unit': 50.0, 'product_id': self.product_service}, {**exempt, 'price_unit': 60.0}], None, False),
            ([{**exempt, 'price_unit': 1999.0}], usd, True),
        ):
            receipt = self.make_invoice('out_receipt', lines=lines, currency=currency)
            with self.subTest(total=receipt.amount_total, currency=receipt.currency_id.name):
                if allowed:
                    self.assertEqual(self.post(receipt).state, 'posted')
                else:
                    with self.assertRaisesRegex(UserError, "cannot exceed"):
                        self.post(receipt)

    def test_discounts(self):
        """
        Discounts are given as a line discount and a global discount, between 0 and 100 %, combined
        on each line; a core discount given to a line is kept as its line discount (PT-29).
        """
        invoice = self.make_invoice(
            lines=[{'price_unit': 1234.568, 'l10n_pt_line_discount': 10.0}, {'price_unit': 756.81}],
            l10n_pt_global_discount=10.0,
        )
        self.assertRecordValues(invoice.invoice_line_ids, [
            {'discount': 19.0, 'price_subtotal': 1000.0},
            {'discount': 10.0, 'price_subtotal': 681.13},
        ])
        self.assertRecordValues(invoice, [{'amount_untaxed': 1681.13, 'amount_tax': 386.66, 'amount_total': 2067.79}])

        given = self.make_invoice(lines=[{'discount': 15.0}], l10n_pt_global_discount=10.0)
        self.assertRecordValues(given.invoice_line_ids, [{'l10n_pt_line_discount': 15.0, 'discount': 23.5}])

        # Over 100 %, the line turns negative, which is refused first.
        for vals, message in (
            ({'l10n_pt_global_discount': 101.0}, "between 0% and 100%|negative lines"),
            ({'l10n_pt_global_discount': -1.0}, "between 0% and 100%"),
        ):
            with self.subTest(vals=vals), self.assertRaisesRegex(ValidationError, message), self.env.cr.savepoint():
                self.make_invoice(**vals)
        with self.assertRaisesRegex(ValidationError, "between 0% and 100%"), self.env.cr.savepoint():
            self.make_invoice(lines=[{'l10n_pt_line_discount': 101.0}])

    def test_numbered_name_locked_except_resequencing(self):
        """
        A numbered invoice keeps its name. Deleting a numbered draft leaves a gap that blocks issuing
        until the later unissued invoices are resequenced, which refuses issued invoices and numbers
        at or below the last issued one, and resyncs the series' counter.
        """
        invoices = self.post(self.make_invoice() + self.make_invoice() + self.make_invoice() + self.make_invoice())
        with self.assertRaisesRegex(UserError, "cannot be changed"):
            invoices[3].name = 'FT 2026/00009'
        self.issue(invoices[0])
        invoices[1].button_draft()
        invoices[1].unlink()
        with self.assertRaisesRegex(UserError, "has a gap: no invoice holds the numbers 2"):
            self.issue(invoices[2])

        def resequence(moves, first_name):
            return self.env['account.resequence.wizard'].with_context(
                active_model='account.move', active_ids=moves.ids,
            ).create({'first_name': first_name, 'ordering': 'keep'}).resequence()

        with self.assertRaisesRegex(UserError, "Issued Portuguese invoices cannot be resequenced"):
            resequence(invoices[0] + invoices[2], 'FT 2026/00001')
        with self.assertRaisesRegex(UserError, "only be renumbered after its last issued number, 1"):
            resequence(invoices[2:], 'FT 2026/00001')
        resequence(invoices[2:], 'FT 2026/00002')
        self.assertEqual(invoices[2:].mapped('name'), ['FT 2026/00002', 'FT 2026/00003'])
        self.issue(invoices[2:])
        self.assertIssued(invoices[2:])
        self.assertEqual(self.post(self.make_invoice()).name, 'FT 2026/00004')

    def test_saft_missing_data_alert(self):
        """A draft lists the SAF-T data it lacks (Despacho 8632/2014 3.4.1, PT-90); a posted invoice lists nothing."""
        product = self._create_product(name='Sem referência')
        product.default_code = False
        invoice = self.make_invoice(lines=[{'product_id': product}])
        self.assertIn("no Internal Reference: Sem referência", invoice.l10n_pt_saft_missing_data)
        self.assertFalse(self.make_invoice().l10n_pt_saft_missing_data)
        product.default_code = 'SEMREF'
        self.post(invoice)
        self.assertFalse(invoice.l10n_pt_saft_missing_data)

    # -------------------------------------------------------------------------
    # Issuing
    # -------------------------------------------------------------------------

    def _send(self, invoice):
        return self.env['account.move.send.wizard'].with_user(invoice.env.user).create({
            'move_id': invoice.id,
            'sending_methods': ['email'],
        }).action_send_and_print()

    def _send_from_cron(self, invoices, authors):
        """Send ``invoices`` as the sending cron does, each queued by its user in ``authors``."""
        for invoice, author in zip(invoices, authors):
            invoice.sending_data = {'author_user_id': author.id, 'author_partner_id': author.partner_id.id}
        self.env['account.move.send']._generate_and_send_invoices(invoices, from_cron=True, sending_methods=['email'])

    def test_triggers_issue(self):
        """
        Printing, an HTML preview, the portal preview, downloading, sending and cancelling each issue the
        invoice, and with it the invoices before it in its series not issued yet, in one signing call
        (PT-128); a pro-forma issues nothing.
        """
        for trigger_name, trigger in (
            ("print", self.print_pdf),
            ("HTML preview", self.preview),
            ("portal preview", lambda invoice: invoice.preview_invoice()),
            ("download", lambda invoice: invoice._get_invoice_legal_documents('pdf')),
            ("download all", lambda invoice: invoice._get_invoice_legal_documents_all()),
            ("send", self._send),
            ("cancel", lambda invoice: invoice.button_cancel()),
        ):
            with self.subTest(trigger=trigger_name):
                earlier, invoice = self.post(self.make_invoice() + self.make_invoice()).with_user(self.billing_user)
                self.signing.reset()
                trigger(invoice)
                self.assertIssued(earlier + invoice)
                self.assertEqual(earlier.state, 'posted')
                self.assertEqual(earlier.l10n_pt_issue_user_id, self.billing_user)
                for move in earlier + invoice:
                    self.assertSignatureValid(move)
                self.assertEqual(self.signing.calls['sign_records'], 1)

        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        invoice.env['ir.actions.report']._render_qweb_html('account.account_invoices', invoice.ids, data={'proforma': True})
        self.assertNotIssued(invoice)

    def test_issuing_records_number_issuer_and_time(self):
        """
        Issuing makes the invoice's name its document number, its ATCUD the series' code and number,
        and records who issued it and when (Portaria 302/2016 4.1.4.3.4, PT-66), as the real user.
        """
        invoice = self.post(self.make_invoice(invoice_date=date(2026, 6, 1))).with_user(self.billing_user)
        with freeze_time('2026-06-15 16:45:00'):
            self.print_pdf(invoice)
        self.assertRecordValues(invoice, [{
            'l10n_pt_document_number': 'FT 2026/00001',
            'l10n_pt_atcud': f'{self.series_ft.at_code}-1',
            'l10n_pt_issue_user_id': self.billing_user.id,
            'l10n_pt_issued_on': datetime(2026, 6, 15, 16, 45),
            'l10n_pt_hashed_on': datetime(2026, 6, 15, 16, 45),
        }])
        self.assertFalse(invoice.env.su)

    def test_issuing_follows_number_order(self):
        """
        The invoices of a series are issued in the order of their numbers (Despacho 8632/2014 2.2.1):
        issuing one issues first those before it not issued yet, signed in number order, and leaves
        those after it alone (PT-128). Only the invoice printed counts as printed.
        """
        invoices = self.post(self.make_invoice() + self.make_invoice() + self.make_invoice() + self.make_invoice()).with_user(self.billing_user)
        self.print_pdf(invoices[2])
        self.assertIssued(invoices[:3])
        self.assertNotIssued(invoices[3])
        self.assertEqual(sorted(p['sorting_key'] for p in self.signing.payloads), [1, 2, 3])
        self.assertChainVerified(invoices[:3])
        self.assertEqual(invoices.mapped('l10n_pt_print_version'), [False, False, 'original', False])

    def test_automatic_issue_issues_earlier_invoices(self):
        """
        An invoice issued as it is posted (`l10n_pt_issue_automatically`: the PoS, online payments)
        issues first the invoices before it in its series not issued yet (PT-128).
        """
        earlier = self.post(self.make_invoice())
        invoice = self.post(self.make_invoice().with_context(l10n_pt_issue_automatically=True))
        self.assertIssued(earlier + invoice)
        self.assertChainVerified(earlier + invoice)

    def test_draft_with_number_blocks_later_invoices(self):
        """
        An invoice reset to draft keeps its number but cannot be issued: the later invoices of its
        series wait for it, whatever issues them.
        """
        invoices = self.post(self.make_invoice() + self.make_invoice()).with_user(self.billing_user)
        invoices[0].button_draft()
        for trigger in (self.print_pdf, self._send):
            with self.subTest(trigger=trigger.__name__), self.assertRaisesRegex(UserError, "Issue FT 2026/00001 first"):
                trigger(invoices[1])
        self.assertNotIssued(invoices)

    def test_cancel_issues_annulled(self):
        """
        Cancelling a numbered invoice not issued yet issues it as annulled: it keeps its number in the
        series and its signature, records who cancelled it and when (PT-66), and its QR code says so.
        """
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        invoice.button_cancel()
        self.assertEqual(invoice.state, 'cancel')
        self.assertIssued(invoice)
        self.assertSignatureValid(invoice)
        self.assertRecordValues(invoice, [{
            'l10n_pt_cancel_user_id': self.billing_user.id,
            'l10n_pt_cancel_date': datetime(2026, 6, 15, 10, 0),
        }])
        self.assertQrFields(invoice, {'E': 'A'})
        self.assertChainVerified(invoice)

    def test_issued_after_series_ended(self):
        """
        An invoice posted on its series' last day is issued after the series ended, with the series'
        code (PT-108). Asserts the reading PT-108 ships while D-22 is open; revisit with D-22's answer.
        """
        self.series_ft.date_end = date(2026, 6, 15)
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        with freeze_time('2026-06-16 09:00:00'):
            self.env.invalidate_all()
            self.assertFalse(self.series_ft.active)
            self.print_pdf(invoice)
        self.assertIssued(invoice)
        self.assertEqual(invoice.l10n_pt_atcud, f'{self.series_ft.at_code}-1')

    def test_company_nif_required(self):
        """
        A document is issued under its company's NIF, which it signs, prints and exports: without a
        valid one, issuing is refused and nothing is issued. The QR code of a document issued before
        cannot be built without it either.
        """
        issued = self.issue(self.post(self.make_invoice()))
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        # Behind the ORM: the partner's VAT check would refuse an invalid NIF.
        for vat in (None, 'PT123456780'):
            with self.subTest(vat=vat):
                self.tamper(self.company_pt.partner_id, 'vat', vat)
                self.env.invalidate_all()
                with self.assertRaisesRegex(RedirectWarning, "Please define the VAT on your company"), self.env.cr.savepoint():
                    self.print_pdf(invoice)
                self.assertNotIssued(invoice)
                with self.assertRaisesRegex(UserError, "The `VAT` of your company should be defined"):
                    issued._l10n_pt_verify_prerequisites_qr_code()
        self.tamper(self.company_pt.partner_id, 'vat', 'PT123456789')
        self.env.invalidate_all()
        self.print_pdf(invoice)
        self.assertIssued(invoice)

    def test_signing_unavailable_interactive(self):
        """When the signing service cannot be reached, printing or sending says so and issues nothing."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.signing.available = False
        for trigger in (self.print_pdf, self._send):
            # A failed request is rolled back, what it wrote before failing included.
            with (
                self.subTest(trigger=trigger.__name__),
                self.assertRaisesRegex(L10nPtSigningUnavailable, "Unable to connect"),
                self.env.cr.savepoint(),
            ):
                trigger(invoice)
            invoice.invalidate_recordset()
        self.assertNotIssued(invoice)

    def test_send_from_cron_as_author(self):
        """The sending cron issues each invoice as the user who asked for its sending, predecessors included."""
        invoices = self.post(self.make_invoice() + self.make_invoice() + self.make_invoice())
        self._send_from_cron(invoices[1:], [self.billing_user, self.env.user])
        self.assertIssued(invoices)
        # The first invoice is issued with the second, as the second's author.
        self.assertEqual(invoices.mapped('l10n_pt_issue_user_id'), self.billing_user + self.billing_user + self.env.user)

    def test_send_from_cron_signing_unavailable(self):
        """
        From the cron, invoices that cannot be issued are not sent, nor kept for the cron, with the
        reason in their chatter; while the service is down no later series is tried.
        """
        invoices = self.post(self.make_invoice() + self.make_invoice('out_receipt'))
        self.signing.available = False
        self._send_from_cron(invoices, [self.billing_user] * 2)
        self.assertNotIssued(invoices)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        for invoice in invoices:
            self.assertFalse(invoice.sending_data)
            self.assertIn("could not be issued, so it was not sent", invoice.message_ids[:1].body)

    def test_send_from_cron_skips_series_that_cannot_issue(self):
        """A series that cannot be issued (here, a gap) is not sent; the other series are."""
        invoices = self.post(self.make_invoice() + self.make_invoice() + self.make_invoice('out_receipt'))
        invoices[0].button_draft()
        self._send_from_cron(invoices[1:], [self.billing_user] * 2)
        self.assertNotIssued(invoices[:2])
        self.assertIssued(invoices[2])
        self.assertIn("Issue FT 2026/00001 first", invoices[1].message_ids[:1].body)

    def test_documents_needing_an_issued_invoice(self):
        """
        A credit note, a debit note, a receipt and a reconciliation reference the invoice's document
        number: they are refused while it is not issued, and issue it under `l10n_pt_issue_automatically`.
        """
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        with self.assertRaisesRegex(UserError, "A credit note needs these invoices to be issued first"):
            self.reverse(invoice)
        with self.assertRaisesRegex(UserError, "A credit note needs these invoices to be issued first"), self.env.cr.savepoint():
            self.post(invoice._reverse_moves())
        with self.assertRaisesRegex(UserError, "A receipt needs these invoices to be issued first"):
            self.make_receipt(invoice)
        if 'debit_origin_id' in invoice._fields:
            with self.assertRaisesRegex(UserError, "A debit note needs these invoices to be issued first"), self.env.cr.savepoint():
                self.post(self.make_invoice(debit_origin_id=invoice.id))

        payment = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_pt.id,
            'amount': invoice.amount_total,
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.post(payment)
        outstanding = payment.move_id.line_ids.filtered(lambda line: line.account_type == 'asset_receivable')
        with self.assertRaisesRegex(UserError, "A payment or reconciliation needs these invoices to be issued first"):
            invoice.js_assign_outstanding_line(outstanding.id)
        self.assertNotIssued(invoice)

        receipt = self.make_receipt(invoice.with_context(l10n_pt_issue_automatically=True))
        self.assertIssued(invoice)
        self.assertIssued(receipt)
        self.assertIn(invoice.payment_state, ('in_payment', 'paid'))

    # -------------------------------------------------------------------------
    # Corrections
    # -------------------------------------------------------------------------

    def _cancel_wizard(self, records, reason='Erro de faturação'):
        return self.env['l10n_pt.cancel'].with_user(self.billing_user).with_context(
            active_model=records._name, active_ids=records.ids,
        ).create({'l10n_pt_cancel_reason': reason})

    def test_credit_note_reason_and_origin(self):
        """A credit note needs a reason, stored for the SAF-T, and references the invoice it rectifies."""
        invoice = self.issue(self.post(self.make_invoice())).with_user(self.billing_user)
        with self.assertRaisesRegex(UserError, "For Credit Notes issued in Portugal, you need to specify a Reason"):
            self.reverse(invoice, reason=False)
        credit_note = self.reverse(invoice, reason='Devolução de mercadoria')
        self.assertRecordValues(credit_note, [{
            'move_type': 'out_refund', 'reversed_entry_id': invoice.id, 'l10n_pt_reversal_reason': 'Devolução de mercadoria',
        }])
        self.issue(self.post(credit_note))
        self.assertIssued(credit_note)
        self.assertEqual(invoice.reversal_move_ids, credit_note)

    def test_credit_note_without_origin_refused(self):
        """A credit note made by hand, without the invoice it rectifies, is not posted."""
        with self.assertRaisesRegex(UserError, "You cannot post a credit note without referencing the original invoice"):
            self.post(self.make_invoice('out_refund'))

    def test_credit_note_cannot_exceed_original(self):
        """The credit notes of an invoice never credit more than it, in quantity or in amount."""
        invoice = self.issue(self.post(self.make_invoice(lines=[{'quantity': 2}])))
        credit_note = self.reverse(invoice)
        # A refused posting rolls back its request, the number it took included.
        for vals, message in (
            ({'quantity': 3}, "quantity exceeding that of the original customer invoice"),
            ({'quantity': 2, 'price_unit': 150.0}, "exceeds the amount of the original customer invoice"),
        ):
            credit_note.invoice_line_ids.write(vals)
            with self.subTest(vals=vals), self.assertRaisesRegex(UserError, message), self.env.cr.savepoint():
                self.post(credit_note)
        credit_note.invoice_line_ids.write({'quantity': 1, 'price_unit': 100.0})
        self.issue(self.post(credit_note))
        self.assertEqual(credit_note.name, 'NC 2026/00001')
        second = self.reverse(invoice)
        second.invoice_line_ids.quantity = 2
        with self.assertRaisesRegex(UserError, "quantity exceeding that of the original customer invoice"), self.env.cr.savepoint():
            self.post(second)

    def test_credit_notes_together_cannot_exceed_original(self):
        """
        The credit notes of an invoice together never credit more than its amount, whatever
        quantities are left; crediting its whole amount reverses it.
        """
        invoice = self.issue(self.post(self.make_invoice(lines=[{'quantity': 5}])))
        first = self.reverse(invoice)
        first.invoice_line_ids.quantity = 2
        self.issue(self.post(first))
        second = self.reverse(invoice)
        # 2 x 100 + 3 x 150 credits 650 of 500, within the quantity.
        second.invoice_line_ids.write({'quantity': 3, 'price_unit': 150.0})
        with (
            self.assertRaisesRegex(UserError, f"in conjunction with {first.name} exceeds the amount on the original customer invoice"),
            self.env.cr.savepoint(),
        ):
            self.post(second)
        # 2 x 100 + 2 x 150 credits the whole 500, with one unit left.
        second.invoice_line_ids.quantity = 2
        self.issue(self.post(second))
        self.assertEqual(invoice.payment_state, 'reversed')
        with self.assertRaisesRegex(UserError, "cannot reverse an invoice that has already been fully reversed"):
            invoice.action_reverse()

    def test_fully_reversed_or_cancelled(self):
        """An invoice fully reversed, or cancelled, is neither cancelled nor reversed again."""
        reversed_invoice = self.issue(self.post(self.make_invoice()))
        self.issue(self.post(self.reverse(reversed_invoice)))
        self.assertEqual(reversed_invoice.payment_state, 'reversed')
        cancelled = self.post(self.make_invoice())
        cancelled.button_cancel()
        for invoice in (reversed_invoice, cancelled):
            with self.subTest(state=invoice.state, payment_state=invoice.payment_state):
                with self.assertRaisesRegex(UserError, "cannot cancel an invoice that has already been fully reversed or cancelled"):
                    invoice.button_cancel()
                with self.assertRaisesRegex(UserError, "cannot reverse an invoice that has already been fully reversed or cancelled"):
                    invoice.action_reverse()

    def test_cancel_refused_while_rectified(self):
        """An invoice rectified by a posted credit or debit note, even partly, is annulled only once the note is (PT-64)."""
        invoice = self.issue(self.post(self.make_invoice(lines=[{'quantity': 2}])))
        credit_note = self.reverse(invoice)
        credit_note.invoice_line_ids.quantity = 1
        self.issue(self.post(credit_note))
        with self.assertRaisesRegex(UserError, f"while a credit or debit note rectifies it. Cancel {credit_note.name} first"):
            invoice.button_cancel()
        credit_note.button_cancel()
        invoice.button_cancel()
        self.assertEqual(invoice.state, 'cancel')

        if 'debit_origin_id' in invoice._fields:
            debited = self.issue(self.post(self.make_invoice()))
            debit_note = self.issue(self.post(self.make_invoice(debit_origin_id=debited.id)))
            with self.assertRaisesRegex(UserError, f"Cancel {debit_note.name} first"):
                debited.button_cancel()

    def test_no_reset_to_draft_once_issued(self):
        """An issued invoice, credit note or annulled invoice cannot go back to draft."""
        invoice = self.issue(self.post(self.make_invoice(lines=[{'quantity': 2}])))
        credit_note = self.reverse(invoice)
        credit_note.invoice_line_ids.quantity = 1
        self.issue(self.post(credit_note))
        cancelled = self.post(self.make_invoice())
        cancelled.button_cancel()
        for move in (invoice, credit_note, cancelled):
            with self.subTest(move=move.name):
                self.assertFalse(move.show_reset_to_draft_button)
                with self.assertRaisesRegex(UserError, "You cannot reset to draft a Portuguese certified document"):
                    move.button_draft()

    def test_cancel_wizard(self):
        """The cancel wizard annuls invoices and receipts with the reason given, and nothing else (PT-118)."""
        invoice = self.issue(self.post(self.make_invoice()))
        self._cancel_wizard(invoice, '  Cliente errado ').button_cancel()
        self.assertRecordValues(invoice, [{
            'state': 'cancel',
            'l10n_pt_cancel_reason': 'Cliente errado',
            'l10n_pt_cancel_user_id': self.billing_user.id,
            'l10n_pt_cancel_date': datetime(2026, 6, 15, 10, 0),
        }])
        self.assertSignatureValid(invoice)
        with self.assertRaisesRegex(UserError, "Only invoices and receipts can be cancelled with this wizard"):
            self._cancel_wizard(self.partner_pt).button_cancel()

    # -------------------------------------------------------------------------
    # Receipts
    # -------------------------------------------------------------------------

    def _payment(self, **vals):
        return self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_pt.id,
            'amount': 100.0,
            'journal_id': self.company_data['default_journal_bank'].id,
            **vals,
        })

    def test_receipt_numbered_at_posting(self):
        """A receipt is issued when posted: RG number, ATCUD, issuer and time; it is not signed."""
        invoice = self.issue(self.post(self.make_invoice()))
        receipt = self.make_receipt(invoice.with_user(self.billing_user))
        self.assertRecordValues(receipt, [{
            'l10n_pt_document_type': 'payment_receipt',
            'l10n_pt_at_series_id': self.series_rg.id,
            'l10n_pt_document_number': 'RG 2026/00001',
            'l10n_pt_atcud': f'{self.series_rg.at_code}-1',
            'l10n_pt_issue_user_id': self.billing_user.id,
            'l10n_pt_issued_on': datetime(2026, 6, 15, 10, 0),
        }])
        self.assertFalse(self.signing.calls['sign_records'] > 1)
        with self.assertRaisesRegex(UserError, "The AT Series of a payment being processed, paid or canceled cannot be changed"):
            receipt.l10n_pt_at_series_id = self.series_factory(name='2026B', document_type='payment_receipt')

    def test_receipt_of_unissued_invoice_refused(self):
        """A receipt references the document number of what it pays: an unissued invoice is refused."""
        invoice = self.post(self.make_invoice())
        payment = self._payment(invoice_ids=[Command.link(invoice.id)])
        with self.assertRaisesRegex(UserError, "A receipt needs these invoices to be issued first"):
            self.post(payment)
        self.assertNotIssued(payment)

    def test_series_of_payments(self):
        """
        Only a PT inbound payment gets a series, valid on its date: not an outbound payment, nor one of
        a non-PT company; dated outside every RG series it is refused (PT-112).
        """
        outbound = self._payment(payment_type='outbound', partner_type='supplier')
        foreign = self.env['account.payment'].with_company(self.company_foreign).create({
            'payment_type': 'inbound', 'partner_type': 'customer', 'partner_id': self.partner_foreign.id,
            'amount': 100.0, 'journal_id': self.company_data_foreign['default_journal_bank'].id,
        })
        self.assertFalse((outbound + foreign).l10n_pt_at_series_id)
        self.post(outbound + foreign)
        self.assertEqual((outbound + foreign).mapped('l10n_pt_document_number'), [False, False])

        self.assertEqual(self._payment().l10n_pt_at_series_id, self.series_rg)
        for day in (date(2025, 12, 30), date(2027, 1, 4)):
            with (
                self.subTest(day=day),
                self.assertRaisesRegex(UserError, "Please select a series for this document"),
                self.env.cr.savepoint(),
            ):
                self._payment(date=day)

    def test_receipt_chronology(self):
        """No receipt is dated before the last one of its series."""
        self.post(self._payment(date=date(2026, 6, 20)))
        with self.assertRaisesRegex(UserError, "dated earlier than the last document issued in this AT series"):
            self.post(self._payment())

    def test_register_payment_outbound(self):
        """Register Payment on a vendor bill and on a customer refund posts, with no AT series (PT-107)."""
        bill = self.post(self.make_invoice('in_invoice', lines=[{'tax_ids': self.tax_purchase_a}]))
        # The invoice is paid first, or its credit note would settle it, leaving nothing to refund.
        invoice = self.issue(self.post(self.make_invoice()))
        self.make_receipt(invoice)
        refund = self.issue(self.post(self.reverse(invoice)))
        for document in (bill, refund):
            with self.subTest(document=document.move_type):
                payment = self.make_receipt(document.with_user(self.billing_user))
                self.assertEqual(payment.payment_type, 'outbound')
                self.assertFalse(payment.l10n_pt_at_series_id)
                self.assertFalse(payment.l10n_pt_document_number)

    def test_register_payment_series(self):
        """On a customer invoice, Register Payment offers only the journal's RG series valid today."""
        self.series_factory(name='2025', document_type='payment_receipt', date_start='2025-01-01', date_end='2025-12-31')
        other_journal = self.company_data['default_journal_bank'].copy({'code': 'BNK9'})
        other_series = self.series_factory(name='2026B', document_type='payment_receipt', journal_id=other_journal.id)
        invoice = self.issue(self.post(self.make_invoice()))
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'journal_id': self.company_data['default_journal_bank'].id,
        })
        self.assertEqual(wizard.available_l10n_pt_at_series_ids, self.series_rg)
        self.assertEqual(wizard.l10n_pt_at_series_id, self.series_rg)
        wizard.journal_id = other_journal
        self.assertEqual((wizard.available_l10n_pt_at_series_ids, wizard.l10n_pt_at_series_id), (other_series, other_series))

    def test_cancel_with_reason(self):
        """Cancelling a receipt records the reason given, when and by whom (PT-66)."""
        receipt = self.make_receipt(self.issue(self.post(self.make_invoice())))
        self.env['l10n_pt.cancel'].with_user(self.billing_user).with_context(
            active_model='account.payment', active_ids=receipt.ids,
        ).create({'l10n_pt_cancel_reason': '  Pagamento duplicado  '}).button_cancel()
        self.assertRecordValues(receipt, [{
            'state': 'canceled',
            'l10n_pt_cancel_reason': 'Pagamento duplicado',
            'l10n_pt_cancel_user_id': self.billing_user.id,
            'l10n_pt_cancel_date': datetime(2026, 6, 15, 10, 0),
            'l10n_pt_document_number': 'RG 2026/00001',
        }])

    def test_payment_mechanism(self):
        """
        Every PT inbound payment method has a mechanism (exported as PaymentMechanism), defaulted from
        its journal type: transfer for a bank, cash for a cash journal; a hand-set one is kept.
        """
        bank_line = self.company_data['default_journal_bank'].inbound_payment_method_line_ids[:1]
        cash_line = self.company_data['default_journal_cash'].inbound_payment_method_line_ids[:1]
        self.assertEqual((bank_line.l10n_pt_payment_mechanism, cash_line.l10n_pt_payment_mechanism), ('TB', 'NU'))
        bank_line.l10n_pt_payment_mechanism = 'MB'
        self.assertEqual(bank_line.l10n_pt_payment_mechanism, 'MB')
        with self.assertRaisesRegex(ValidationError, "Set a payment mechanism"):
            bank_line.l10n_pt_payment_mechanism = False
        self.company_data['default_journal_bank'].outbound_payment_method_line_ids[:1].l10n_pt_payment_mechanism = False

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # A fixed number of queries per series or company, not per document (AGENTS.md: no per-record
    # queries), measured as independence from the number of documents rather than as exact budgets,
    # which would move with every installed PT module.

    def test_series_lookup_per_group(self):
        """
        Computing the series of drafts searches once per company, journal, type and date, however many
        drafts (PT-119). Only the lookups are counted: writing the series costs core a query per move.
        """
        def series_lookups(count):
            moves = self.env['account.move'].concat(*(self.make_invoice() for _i in range(count)))
            # Drafts get their series when created: clear it, so that the compute searches again.
            for move in moves:
                self.tamper(move, 'l10n_pt_at_series_id', None)
            self.env.flush_all()
            self.env.invalidate_all()
            queries = []
            execute = Cursor.execute

            def logged_execute(cr, query, params=None, log_exceptions=True):
                queries.append(str(getattr(query, 'code', query)))
                return execute(cr, query, params, log_exceptions)

            with patch.object(Cursor, 'execute', logged_execute):
                moves._compute_l10n_pt_at_series_id()
            self.assertEqual(moves.l10n_pt_at_series_id, self.series_ft)
            return len([q for q in queries if re.search(r'FROM "(account_move|l10n_pt_at_series)" WHERE', q)])

        self.assertEqual(series_lookups(1), series_lookups(8))

    @unittest.skip("PT-7 (parked): the series' sequence is searched once per document numbered")
    def test_batch_numbering_looks_sequence_up_once(self):
        """Posting a batch in one series looks its sequence up once (PT-7)."""
        moves = self.env['account.move'].concat(*(self.make_invoice() for _i in range(5)))
        Series = self.registry['l10n_pt.at.series']
        with patch.object(Series, '_l10n_pt_get_document_number_sequence', autospec=True, side_effect=Series._l10n_pt_get_document_number_sequence) as lookup:
            self.post(moves)
        self.assertEqual(lookup.call_count, 1)
