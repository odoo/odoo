# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountCZ(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('cz')
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_usd = cls.env.ref('base.USD')
        cls.other_currency = cls.setup_other_currency('EUR', rates=[
            ('2026-06-01', 1),
            ('2026-06-02', 2),
            ('2026-06-03', 3)])
        cls.invoice_a = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2024-07-10',
            'currency_id': cls.currency_usd.id,
            'invoice_line_ids': [Command.create({
                'quantity': 1.0,
                'price_unit': 1000.0,
            })],
        })

    def test_cz_out_invoice_onchange_accounting_date(self):
        self.invoice_a.taxable_supply_date = '2024-03-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-03-31'))
        self.assertEqual(self.invoice_a.invoice_currency_rate, 1.0)
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 1.0)

        self.env['res.currency.rate'].create({
            'name': '2024-04-28',
            'rate': 0.042799058421,
            'currency_id': self.currency_usd.id,
        })

        self.invoice_a.taxable_supply_date = '2024-05-31'
        self.assertEqual(self.invoice_a.date, fields.Date.to_date('2024-05-31'))
        self.assertEqual(self.invoice_a.invoice_currency_rate, 0.042799058421)
        self.assertEqual(self.invoice_a.invoice_line_ids[0].currency_rate, 0.042799058421)

    def test_cz_bank_rec_no_taxable_supply_date(self):
        """
        Test that when creating a new bank reconciliation, the taxable payable date is not set automatically.
        """
        st_line = self.env['account.bank.statement.line'].create({
            'amount': 100,
            'date': '2024-12-31',
        })
        wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
        wizard._action_validate()

        inv_line = self.env['account.move'].search([('statement_line_id', '=', st_line.id)])
        self.assertNotEqual(inv_line.taxable_supply_date, st_line.date)

    def test_cz_taxable_supply_date_updates_when_reversing_invoice(self):
        self.invoice_a.taxable_supply_date = '2024-03-31'
        self.invoice_a.partner_id = self.partner_a
        self.invoice_a.action_post()
        reversal_wizard = self.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=self.invoice_a.ids
        ).create({
            'date': '2024-07-15',
            'reason': 'Test',
            'journal_id': self.invoice_a.journal_id.id,
        })
        action = reversal_wizard.reverse_moves()
        refund_move = self.env['account.move'].browse(action['res_id'])
        self.assertEqual(refund_move.taxable_supply_date, fields.Date.to_date('2024-07-15'))
        self.assertEqual(refund_move.date, fields.Date.to_date('2024-07-15'))

    @freeze_time('2026-06-02')
    def test_currency_rate_manual_change(self):
        """
        Ensure that if invoice_currency_rate is manually set and invoice_date is not set,
        posting the invoice doesn't change the currency rate back to default
        """
        invoice1 = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_date': False,
            'taxable_supply_date': '2026-06-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 60})],
            'currency_id': self.other_currency.id,
        }])
        self.assertEqual(invoice1.invoice_currency_rate, 1.0)
        self.env.cr.execute(f""" UPDATE account_move SET create_date = '2026-06-02' where id  = {invoice1.id}""")
        invoice1.invalidate_recordset(['create_date'])
        # currency rate of the invoice creation date that will be computed on action_post
        invoice1.invoice_currency_rate = 2
        invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
        invoice1.button_draft()
        invoice1.invoice_date = False
        invoice1.invoice_currency_rate = 2
        with freeze_time('2026-06-03'):
            invoice1.action_post()
        self.assertRecordValues(invoice1.line_ids, [
            {'amount_currency':   -60.0, 'balance':   -30.0},  # Product line
            {'amount_currency':    60.0, 'balance':    30.0},  # Receivable line
        ])
