# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
            'order_line': [(0, 0, {
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
                (0, 0, {
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'unit_amount': self.company_data['product_order_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_order_sales_price'].id,
                    'unit_amount': self.company_data['product_order_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_5',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet.approve_expense_sheets()
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

    def test_distinguish_expense_lines_distinct_employees(self):
        """
            Test: same expense product by different employees to re-invoice
                is represented in different sale order lines
        """

        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
        })

        sale_order._compute_tax_id()
        sale_order.action_confirm()

        expense_sheet1 = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'test_expense',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                })
            ]
        })
        expense_sheet1.approve_expense_sheets()
        expense_sheet1.action_sheet_move_create()

        expense_sheet2 = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee_a.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'test_expense',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee_a.id,
                    'sale_order_id': sale_order.id,
                })
            ]
        })
        expense_sheet2.approve_expense_sheets()
        expense_sheet2.action_sheet_move_create()

        expense_sheet3 = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee_a.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    'name': 'test_expense',
                    'date': '2016-01-01',
                    'product_id': self.company_data['product_delivery_sales_price'].id,
                    'unit_amount': self.company_data['product_delivery_sales_price'].list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee_a.id,
                    'sale_order_id': sale_order.id,
                })
            ]
        })
        expense_sheet3.approve_expense_sheets()
        expense_sheet3.action_sheet_move_create()

        sales_order_lines = self.env['sale.order'].browse(sale_order.id).order_line

        # verify 2 distinct sale order lines were created for same product
        # first has 1 qty to invoice ( expense sheet 1 )
        # second has 2 qty to invoice ( expense sheet 2, 3 )

        self.assertEqual(len(sales_order_lines), 2)

        self.assertTrue(sales_order_lines[0]['qty_to_invoice'], sales_order_lines[0]['qty_delivered'])
        self.assertTrue(int(sales_order_lines[0]['qty_to_invoice']), 1)
        self.assertTrue(sales_order_lines[0]['name'], f'{self.expense_employee.name}: test_expense')

        self.assertTrue(sales_order_lines[-1]['qty_to_invoice'], sales_order_lines[-1]['qty_delivered'])
        self.assertTrue(int(sales_order_lines[-1]['qty_to_invoice']), 2)
        self.assertTrue(sales_order_lines[-1]['name'], f'{self.expense_employee_a.name}: test_expense')
