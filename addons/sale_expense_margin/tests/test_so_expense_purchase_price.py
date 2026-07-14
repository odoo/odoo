# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged

@tagged('-at_install', 'post_install')
class TestExpenseMargin(TestExpenseCommon):

    def test_expense_reinvoice_purchase_price(self):
        # re-invoiceable products
        product_with_cost = self.product_a
        product_with_cost.write({'standard_price': 1000, 'expense_policy': 'sales_price'})
        product_with_no_cost = self.product_c
        product_with_no_cost.write({'expense_policy': 'sales_price'})

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
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

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2020-10-12',
            'expense_line_ids': [
                # expense with zero cost product, with 15% tax
                Command.create({
                    'name': 'expense_1',
                    'date': '2020-10-07',
                    'product_id': product_with_no_cost.id,
                    'total_amount_currency': 100,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                # expense with zero cost product, with no tax
                Command.create({
                    'name': 'expense_2',
                    'date': '2020-10-07',
                    'product_id': product_with_no_cost.id,
                    'total_amount_currency': 100,
                    'tax_ids': False,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id
                }),
                # expense with product with cost (1000), with 15% tax
                Command.create({
                    'name': 'expense_3',
                    'date': '2020-10-07',
                    'product_id': product_with_cost.id,
                    'quantity': 3,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id
                }),
                # expense with product with cost (1000), with no tax
                Command.create({
                    'name': 'expense_4',
                    'date': '2020-10-07',
                    'product_id': product_with_cost.id,
                    'quantity': 5,
                    'tax_ids': False,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id
                }),
            ],
        })

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        for line, expected_purchase_price in zip(sale_order.order_line[1:], [86.96, 100.0, 869.5666667, 1000.0]):
            self.assertAlmostEqual(line.purchase_price, expected_purchase_price)
            self.assertTrue(line.is_expense)
