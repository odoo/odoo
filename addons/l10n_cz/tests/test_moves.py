# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
