# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestReInvoice(TestExpenseCommon, TestCommonSaleNoChart):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        super().setUpExpenseProducts()

        cls.price_list = cls.env['product.pricelist'].create({
            'name': 'default_price_list_company_1',
            'sequence': 1,
            'company_id': cls.company_data['company'].id,
            'currency_id': cls.company_data['currency'].id,
        })

    def test_expenses_reinvoice(self):
        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product_ordered_cost.name,
                'product_id': self.product_ordered_cost.id,
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
                    'product_id': self.product_ordered_cost.id,
                    'unit_amount': self.product_ordered_cost.list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_2',
                    'date': '2016-01-01',
                    'product_id': self.product_deliver_cost.id,
                    'unit_amount': self.product_deliver_cost.list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_3',
                    'date': '2016-01-01',
                    'product_id': self.product_order_sales_price.id,
                    'unit_amount': self.product_order_sales_price.list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_4',
                    'date': '2016-01-01',
                    'product_id': self.product_deliver_sales_price.id,
                    'unit_amount': self.product_deliver_sales_price.list_price,
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                (0, 0, {
                    'name': 'expense_5',
                    'date': '2016-01-01',
                    'product_id': self.product_no_expense.id,
                    'unit_amount': self.product_no_expense.list_price,
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
                'product_uom_qty': 0.0,
                'is_expense': True,
            },
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 0.0,
                'is_expense': True,
            },
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 0.0,
                'is_expense': True,
            },
            {
                'qty_delivered': 1.0,
                'product_uom_qty': 0.0,
                'is_expense': True,
            },
        ])

        # 'qty_delivered_method' is not checked on the first line because it could be multiple things depending if
        # 'sale_stock' is installed or not.
        self.assertRecordValues(sale_order.order_line[1:], [
            {'qty_delivered_method': 'analytic'},
            {'qty_delivered_method': 'analytic'},
            {'qty_delivered_method': 'analytic'},
            {'qty_delivered_method': 'analytic'},
        ])
