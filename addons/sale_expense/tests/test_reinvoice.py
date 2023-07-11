# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestReInvoice(TestExpenseCommon, TestSaleCommon):

    def test_expenses_reinvoice(self):
        (self.company_data['product_order_sales_price'] + self.company_data['product_delivery_sales_price']).write({
            'can_be_expensed': True,
        })

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_sales_price'].name,
                'product_id': self.company_data['product_order_sales_price'].id,
                'product_uom_qty': 2.0,
                'price_unit': 1000.0,
            })],
        })
        sale_order.action_confirm()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'total_amount_currency': self.company_data['product_order_sales_price'].list_price,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'total_amount_currency': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'total_amount_currency': self.company_data['product_order_sales_price'].list_price,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'total_amount_currency': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_5',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'total_amount_currency': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(sale_order.order_line, [
            # Original SO line:
            {
                'qty_delivered': 0.0,
                'product_uom_qty': 2.0,
                'is_expense': False,
            },
            # Expense lines:
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
            {
                'qty_delivered': 3.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
        ])

        self.assertRecordValues(sale_order.order_line[1:], [
            {'qty_delivered_method': 'analytic'},
            {'qty_delivered_method': 'analytic'},
            {'qty_delivered_method': 'analytic'},
        ])

    def test_expenses_reinvoice_analytic_distribution(self):
        """Test expense line with multiple analytic accounts is reinvoiced correctly"""

        (self.company_data['product_order_sales_price'] + self.company_data['product_delivery_sales_price']).write({
            'can_be_expensed': True,
        })

        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_sales_price'].name,
                'product_id': self.company_data['product_order_sales_price'].id,
                'product_uom_qty': 2.0,
                'price_unit': 1000.0,
            })],
        })
        sale_order.action_confirm()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'quantity': 2,
                    'analytic_distribution': {self.analytic_account_1.id: 50, self.analytic_account_2.id: 50},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(sale_order.order_line, [
            # Original SO line:
            {
                'qty_delivered': 0.0,
                'product_uom_qty': 2.0,
                'is_expense': False,
            },
            # Expense lines:
            {
                'qty_delivered': 2.0,
                'product_uom_qty': 2.0,
                'is_expense': True,
            },
        ])
