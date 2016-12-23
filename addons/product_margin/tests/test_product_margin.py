# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools import convert_file
from odoo.tests import common
from odoo.modules.module import get_module_resource


class TestMargin(common.TransactionCase):

    def _load(self, module, *args):
        convert_file(self.cr, 'product_margin',
                           get_module_resource(module, *args),
                           {}, 'init', False, 'test', self.registry._assertion_report)

    def test_00_product_margin(self):
        "Create customer and supplier invoices with product 'iPad Mini' to test margins based on those invoices."
        self._load('account', 'test', 'account_minimal_test.xml')

        AccountInvoice = self.env['account.invoice']
        ProductMargin = self.env['report.product.margin']

        product_ipad = self.env.ref('product.product_product_6')

        acc_receivable_id = self.ref('product_margin.a_recv')
        acc_payable_id = self.ref('product_margin.a_pay')
        acc_revenue_id = self.ref('product_margin.a_sale')
        acc_expense_id = self.ref('product_margin.a_expense')
        partner2_id = self.ref('base.res_partner_2')

        # Update company currency EUR to USD to perform test cases
        self.env.ref('base.main_company').write({
            'currency_id': self.ref("base.USD")
        })

        # Create first customer invoice and validate it.
        AccountInvoice.create({
            'name': 'Test Customer Invoice',
            'reference_type': 'none',
            'type': 'out_invoice',
            'partner_id': partner2_id,
            'account_id': acc_receivable_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_ipad.id,
                'quantity': 1,
                'account_id': acc_revenue_id,
                'name': 'Test customer product',
                'price_unit': product_ipad.list_price,
            })]
        }).action_invoice_open()
        # Search margin record of 'iPad Mini'
        margin = ProductMargin.search([('product_id', '=', product_ipad.id)], limit=1)
        # Test total margin on 'iPad Mini'
        self.assertEquals(margin.total_margin, 320.00, 'Wrong value of total margin')

        # Create first supplier invoice and validate it
        AccountInvoice.create({
            'name': 'Test Supplier Invoice',
            'reference_type': 'none',
            'type': 'in_invoice',
            'partner_id': partner2_id,
            'account_id': acc_payable_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_ipad.id,
                'quantity': 1,
                'account_id': acc_expense_id,
                'name': 'Test supplier product',
                'price_unit': product_ipad.standard_price,
            })]
        }).action_invoice_open()
        # Test total margin on 'iPad Mini'
        self.assertEquals(margin.total_margin, -480.00, 'Wrong value of total margin')

        # Create second customer invoice with changed unit price, i.e. 275 USD, and validate it
        AccountInvoice.create({
            'name': 'Test Customer Invoice',
            'reference_type': 'none',
            'type': 'out_invoice',
            'partner_id': partner2_id,
            'account_id': acc_receivable_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_ipad.id,
                'quantity': 1.0,
                'account_id': acc_revenue_id,
                'name': 'Test customer product',
                'price_unit': 275,
            })]
        }).action_invoice_open()
        # Test new margin value for 'iPad Mini'
        self.assertEquals(margin.total_margin, -205.00, 'Wrong value of total margin!')

        # Create second supplier invoice with changed cost price, i.e. 750 USD, and validate it
        AccountInvoice.create({
            'name': 'Test Supplier Invoice',
            'reference_type': 'none',
            'type': 'in_invoice',
            'partner_id': partner2_id,
            'account_id': acc_payable_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_ipad.id,
                'quantity': 1.0,
                'account_id': acc_expense_id,
                'name': 'Test suppler product',
                'price_unit': 750,
            })]
        }).action_invoice_open()

        # Test all function of product margin
        self.assertEquals(margin.total_margin, -955.00, 'Wrong value of total margin!')
        self.assertEquals(margin.expected_margin, -960.00, 'Wrong value of expected margin!')
        self.assertEquals(margin.turnover, 595.00, 'Wrong value of turnover!')
        self.assertEquals(margin.total_cost, 1550.00, 'Wrong value of total cost!')
        self.assertEquals(margin.sales_gap, 45.00, 'Wrong value of sales gap!')
        self.assertEquals(margin.purchase_gap, 50.00, 'Wrong value of purchase gap!')
        self.assertEquals(margin.sale_avg_price, 297.50, 'Wrong value of sale average!')
        self.assertEquals(margin.purchase_avg_price, 775.00, 'Wrong purchase average!')
        self.assertEquals(margin.sale_expected, 640.00, 'Wrong value of sale expected!')
        self.assertEquals(margin.normal_cost, 1600.00, 'Wrong value of purchase expected!')

        # Create new customer invoice with other than USD currency, let's create it with INR, and validate it
        AccountInvoice.create({
            'name': 'Test Customer Invoice',
            'reference_type': 'none',
            'type': 'out_invoice',
            'partner_id': partner2_id,
            'company_id': self.ref('base.main_company'),
            'currency_id': self.ref('base.INR'),
            'account_id': acc_receivable_id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product_ipad.id,
                'quantity': 1.0,
                'account_id': acc_revenue_id,
                'name': 'Test customer product',
                'price_unit': product_ipad.list_price,
            })]
        }).action_invoice_open()

        # Search margin records of 'iPad Mini'(there should be 2 records, one with USD and other with INR as currency)
        total_margin = 0.00
        turnover = 0.00
        for margin in ProductMargin.search([('product_id', '=', product_ipad.id)]):
            total_margin += margin.total_margin
            turnover += margin.turnover

        # Test total margin with different currency rate
        self.assertEquals(total_margin, -946.84, 'Wrong value of margin with currency!')
        self.assertEquals(turnover, 603.16, 'Wrong value of turnover with currency!')
