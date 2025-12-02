# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpenseMargin(TestExpenseCommon):

    def test_expense_reinvoice_purchase_price(self):
        # re-invoiceable products
        product_with_cost = self.product_a
        product_with_cost.write({'standard_price': 1000, 'expense_policy': 'sales_price'})
        product_with_no_cost = self.product_c
        product_with_no_cost.write({'expense_policy': 'sales_price'})

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(
            mail_notrack=True,
            mail_create_nolog=True,
        ).sudo().create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': product_with_cost.name,
                'product_id': product_with_cost.id,
                'product_uom_qty': 2.0,
            })],
        })

        sale_order.action_confirm()

        expense = self.create_expenses([
            {
                # expense with zero cost product, with 15% tax
                'name': 'expense_1',
                'date': '2020-10-07',
                'product_id': product_with_no_cost.id,
                'total_amount_currency': 100,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                'sale_order_id': sale_order.id,
            },
            {
                # expense with zero cost product, with no tax
                'name': 'expense_2',
                'date': '2020-10-07',
                'product_id': product_with_no_cost.id,
                'total_amount_currency': 100,
                'tax_ids': False,
                'sale_order_id': sale_order.id
            },
            {
                # expense with product with cost (1000), with 15% tax
                'name': 'expense_3',
                'date': '2020-10-07',
                'product_id': product_with_cost.id,
                'quantity': 3,
                'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                'sale_order_id': sale_order.id
            },
            {
                # expense with product with cost (1000), with no tax
                'name': 'expense_4',
                'date': '2020-10-07',
                'product_id': product_with_cost.id,
                'quantity': 5,
                'tax_ids': False,
                'sale_order_id': sale_order.id
            },
        ]).sorted('name')

        expense.action_submit()
        expense._do_approve()  # Skip duplicate wizard
        self.post_expenses_with_wizard(expense)

        self.assertRecordValues(sale_order.order_line, [
            {'purchase_price': 1000.00, 'is_expense': False},
            # Expense lines:
            {'purchase_price':   86.96, 'is_expense': True},
            {'purchase_price':  100.00, 'is_expense': True},
            {'purchase_price':  869.57, 'is_expense': True},
            {'purchase_price': 1000.00, 'is_expense': True},
        ])
