# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleCreateInvoiceMultiCompany(TestSaleCommon):

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

        # A confirmed order owned by company B, priced so the invoice total is
        # not round and a rounding line is required.
        cls.order_b = cls.env['sale.order'].with_company(cls.company_data_2['company']).create({
            'partner_id': cls.partner_a.id,
            'company_id': cls.company_data_2['company'].id,
            'order_line': [Command.create({
                'product_id': cls.company_data_2['product_service_order'].id,
                'product_uom_qty': 1,
                'price_unit': 100.42,
            })],
        })
        cls.order_b.action_confirm()

    def test_create_invoices_cross_company_cash_rounding(self):
        # A global ir.default sets the cash rounding on every invoice, so the
        # generated move gets it at create time while the main company is active.
        self.env['ir.default'].set('account.move', 'invoice_cash_rounding_id', self.cash_rounding.id)

        order = self.order_b.with_company(self.company_data['company'])
        self.assertEqual(order.env.company, self.company_data['company'])

        invoices = order._create_invoices()
        self.assertTrue(invoices, "The invoice should have been created.")
        self.assertEqual(invoices.company_id, self.company_data_2['company'])

        rounding_line = invoices.line_ids.filtered(lambda line: line.display_type == 'rounding')
        self.assertTrue(rounding_line, "A cash-rounding line should have been added.")
        self.assertEqual(
            rounding_line.account_id.company_ids,
            self.company_data_2['company'],
            "The rounding line must use the invoice's own company account.",
        )
