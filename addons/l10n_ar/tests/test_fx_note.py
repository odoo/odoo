# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.l10n_ar.tests.common import TestArCommon


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestArFxNote(TestArCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls._create_journal('preprinted')
        cls.partner = cls.res_partner_adhoc
        cls.usd = cls.setup_other_currency('USD', rates=[
            ('2026-10-01', 0.5),
            ('2026-10-05', 0.01),
            ('2026-10-06', 1 / 110),
            ('2026-10-12', 0.25),
            ('2026-10-15', 0.75),
            ('2026-10-20', 1.0),
        ])

    def test_fx_debit_note(self):
        invoice = self._create_invoice_ar(invoice_date='2026-10-02', currency_id=self.usd, journal_id=self.journal, post=True)
        self._register_payment(invoice, payment_date='2026-10-13')
        paid_state = invoice.payment_state
        self.assertTrue(invoice.l10n_ar_fx_note_pending)

        action = invoice.action_l10n_ar_generate_fx_note()
        note = self.env['account.move'].browse(action['res_id'])
        self.assertRecordValues(note, [{
            'move_type': 'out_invoice',
            'state': 'draft',
            'debit_origin_id': invoice.id,
            'currency_id': self.env.ref('base.ARS').id,
            'journal_id': self.journal.id,
            'l10n_latam_document_type_id': self.env.ref('l10n_ar.dc_a_nd').id,
            'amount_total': 242.0,
        }])
        self.assertRecordValues(note.invoice_line_ids, [{
            'price_unit': 200.0,
            'tax_ids': self.tax_21.ids,
            'account_id': self.company_ri.income_currency_exchange_account_id.id,
        }])
        self.assertFalse(invoice.l10n_ar_fx_note_pending)

        note.action_post()
        note.button_draft()
        note.action_post()
        exchange_move = invoice.line_ids.exchange_move_ids
        self.assertRecordValues(exchange_move.reversal_move_ids, [{'state': 'posted', 'date': note.date, 'ref': note.name}])
        self.assertEqual(len(invoice.message_ids.filtered(lambda msg: exchange_move.name in (msg.body or ''))), 1)
        self.assertRecordValues(invoice | note, [{'payment_state': paid_state}, {'payment_state': 'paid'}])

    def test_fx_credit_note_vat_split_and_release(self):
        loss_invoice = self._create_invoice_ar(invoice_date='2026-10-02', currency_id=self.usd, journal_id=self.journal, post=True)
        split_invoice = self._create_invoice_ar(
            invoice_date='2026-10-06', currency_id=self.usd, journal_id=self.journal, post=True,
            invoice_line_ids=[
                self._prepare_invoice_line(price_unit=10, tax_ids=self.tax_21),
                self._prepare_invoice_line(price_unit=10, tax_ids=self.tax_10_5),
            ])
        rounding_invoice = split_invoice.copy({'invoice_date': '2026-10-06'})
        rounding_invoice.action_post()
        zero_invoice = self._create_invoice_ar(invoice_date='2026-10-02', currency_id=self.usd, journal_id=self.journal, post=True)
        self._register_payment(loss_invoice, payment_date='2026-10-21')
        self._register_payment(split_invoice, payment_date='2026-10-07')
        self._register_payment(rounding_invoice, payment_date='2026-10-16')
        self._register_payment(zero_invoice, payment_date='2026-10-13', amount=30.25)
        self._register_payment(zero_invoice, payment_date='2026-10-16')
        self.assertTrue(zero_invoice.line_ids.exchange_move_ids)
        self.assertFalse(zero_invoice.l10n_ar_fx_note_pending)

        notes = self.env['account.move'].search(
            (loss_invoice | split_invoice | rounding_invoice).action_l10n_ar_generate_fx_note()['domain'])
        rounding_note = notes.filtered(lambda note: note.reversed_entry_id == rounding_invoice)
        exchange_lines = rounding_invoice.line_ids.exchange_move_ids.line_ids
        self.assertAlmostEqual(rounding_note.amount_total, -sum(
            exchange_lines.filtered(lambda line: line.account_type == 'asset_receivable').mapped('balance')))
        credit_note = notes.filtered(lambda note: note.reversed_entry_id == loss_invoice)
        debit_note = notes.filtered(lambda note: note.debit_origin_id == split_invoice)
        self.assertRecordValues(credit_note, [{
            'move_type': 'out_refund',
            'l10n_latam_document_type_id': self.env.ref('l10n_ar.dc_a_nc').id,
            'amount_total': 121.0,
        }])
        self.assertEqual(credit_note.invoice_line_ids.account_id, self.company_ri.expense_currency_exchange_account_id)
        self.assertRecordValues(debit_note.invoice_line_ids, [
            {'price_unit': 100.0, 'price_total': 121.0, 'tax_ids': self.tax_21.ids},
            {'price_unit': 100.0, 'price_total': 110.5, 'tax_ids': self.tax_10_5.ids},
        ])

        credit_note.action_post()
        self.assertEqual(credit_note.payment_state, 'reversed')

        debit_note.unlink()
        self.assertRecordValues(loss_invoice | split_invoice, [
            {'l10n_ar_fx_note_pending': False}, {'l10n_ar_fx_note_pending': True},
        ])
        split_invoice.line_ids.exchange_move_ids._reverse_moves(cancel=True)
        self.assertFalse(split_invoice.l10n_ar_fx_note_pending)
        with self.assertRaisesRegex(UserError, "None of the selected invoices have an exchange difference pending"):
            (loss_invoice | split_invoice).action_l10n_ar_generate_fx_note()
