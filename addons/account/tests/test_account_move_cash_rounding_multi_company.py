# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveCashRoundingMultiCompany(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        # Company-dependent profit/loss accounts, set per company.
        cls.cash_rounding = cls.env['account.cash.rounding'].create({
            'name': "Round to 1",
            'rounding': 1.0,
            'rounding_method': 'HALF-UP',
            'strategy': 'add_invoice_line',
        })
        cls.cash_rounding.with_company(cls.company_data['company']).write({
            'profit_account_id': cls.company_data['default_account_revenue'].id,
            'loss_account_id': cls.company_data['default_account_expense'].id,
        })
        cls.cash_rounding.with_company(cls.company_data_2['company']).write({
            'profit_account_id': cls.company_data_2['default_account_revenue'].id,
            'loss_account_id': cls.company_data_2['default_account_expense'].id,
        })

    def test_cash_rounding_resolves_invoice_company(self):
        # A global ir.default sets the cash rounding on every invoice, so the
        # move gets it at create time while the main company is active.
        self.env['ir.default'].set('account.move', 'invoice_cash_rounding_id', self.cash_rounding.id)
        self.assertEqual(self.env.company, self.company_data['company'])

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company_data_2['company'].id,
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1,
                'price_unit': 100.42,
                'tax_ids': [Command.clear()],
            })],
        })

        rounding_line = move.line_ids.filtered(lambda line: line.display_type == 'rounding')
        self.assertTrue(rounding_line, "A cash-rounding line should have been added.")
        self.assertEqual(
            rounding_line.account_id.company_ids,
            self.company_data_2['company'],
            "The rounding line must use the invoice's own company account.",
        )
