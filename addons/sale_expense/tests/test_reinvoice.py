# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestReInvoice(TestExpenseCommon, TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data.update({
            'service_order_sales_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_order_sales_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'sales_price',
                'taxes_id': [Command.set([])],
                'supplier_taxes_id': [Command.set([])],
                'can_be_expensed': True,
            }),
            'service_delivery_sales_price': cls.env['product.product'].with_company(cls.company_data['company']).create({
                'name': 'service_order_sales_price',
                'categ_id': cls.company_data['product_category'].id,
                'standard_price': 235.0,
                'list_price': 280.0,
                'type': 'service',
                'weight': 0.01,
                'uom_id': cls.env.ref('uom.product_uom_unit').id,
                'uom_po_id': cls.env.ref('uom.product_uom_unit').id,
                'default_code': 'FURN_9999',
                'invoice_policy': 'order',
                'expense_policy': 'sales_price',
                'taxes_id': [Command.set([])],
                'supplier_taxes_id': [Command.set([])],
                'can_be_expensed': True,
            }),
        })

    def test_expenses_reinvoice(self):
        """
        Test that expenses are re-invoiced correctly and that the quantity is updated when it has to.
            - Lines are never grouped together (even if reinvoced at sale price and with a re-invoice delivered policy)
            - When posting an expense, it creates the corresponding sol with the expense quantity
            - The quantities ordered and delivered are reset to 0 when:
                - the expense sheet is unposted
                - the expense move is reversed
                - the expense move is reset to draft
        """
        # create SO line and confirm SO (with only one line)
        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price',
                # Using the same name as one of the expense
                'product_id': self.company_data['product_order_sales_price'].id,
                'product_uom_qty': 3.0,
                'price_unit': self.company_data['product_order_sales_price'].standard_price,
            })],
        })
        sale_order.action_confirm()

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'Reset expense test',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_1 invoicing=order, expense=sales_price',
                    'date': '2016-01-01',
                    'product_id': self.company_data['service_order_sales_price'].id,
                    'unit_amount': self.company_data['service_order_sales_price'].standard_price,
                    'quantity': 1,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_2 invoicing=order, expense=sales_price',
                    'date': '2016-01-02',
                    'product_id': self.company_data['service_order_sales_price'].id,
                    'unit_amount': self.company_data['service_order_sales_price'].standard_price,
                    'quantity': 2,
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_3 invoicing=delivery, expense=sales_price',
                    'date': '2016-01-03',
                    'product_id': self.company_data['service_delivery_sales_price'].id,
                    'unit_amount': self.company_data['service_delivery_sales_price'].standard_price,
                    'quantity': 3,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_4 invoicing=delivery, expense=sales_price',
                    'date': '2016-01-03',
                    'product_id': self.company_data['service_delivery_sales_price'].id,
                    'unit_amount': self.company_data['service_delivery_sales_price'].standard_price,
                    'quantity': 4,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # We also need to test "duplicates" aka very similar expenses
        expense_sheet_copy = self.env['hr.expense.sheet'].create({
            'name': 'Reset expense test copy',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                Command.create({
                    'name': 'expense_3 invoicing=delivery, expense=sales_price copy',
                    'date': '2016-01-03',
                    'product_id': self.company_data['service_delivery_sales_price'].id,
                    'unit_amount': self.company_data['service_delivery_sales_price'].standard_price,
                    'quantity': 3,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
                Command.create({
                    'name': 'expense_4 invoicing=delivery, expense=sales_price copy',
                    'date': '2016-01-03',
                    'product_id': self.company_data['service_delivery_sales_price'].id,
                    'unit_amount': self.company_data['service_delivery_sales_price'].standard_price,
                    'quantity': 4,
                    'analytic_distribution': {self.analytic_account_1.id: 100},
                    'employee_id': self.expense_employee.id,
                    'sale_order_id': sale_order.id,
                }),
            ],
        })

        expense_sheet_copy.approve_expense_sheets()
        expense_sheet_copy.action_sheet_move_create()
        #pylint: disable=bad-whitespace
        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'is_expense': False, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'is_expense':  True, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 2.0, 'product_uom_qty': 2.0, 'is_expense':  True, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
        ])

        expense_sheet.action_unpost()  # Lines [0-4] quantities are set to 0
        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
        ])

        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()  # Lines [1-4] are still at 0 but new lines are created (stable limitation)

        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 2.0, 'product_uom_qty': 2.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
        ])

        expense_sheet.account_move_id.button_draft() # Lines [7-11] quantities are set to 0
        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
        ])

        expense_sheet.account_move_id.action_post()  # Lines [7-11] are still at 0 but new lines are created (stable limitation)
        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 1.0, 'product_uom_qty': 1.0, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 2.0, 'product_uom_qty': 2.0, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
        ])

        expense_sheet.account_move_id._reverse_moves() # Lines [7-11] quantities are set to 0
        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 0.0, 'product_uom_qty': 3.0, 'is_expense': False, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 3.0, 'product_uom_qty': 3.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 4.0, 'product_uom_qty': 4.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price copy'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_1 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_2 invoicing=order, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_3 invoicing=delivery, expense=sales_price'},
            {'qty_delivered': 0.0, 'product_uom_qty': 0.0, 'is_expense':  True, 'name': 'expense_employee: expense_4 invoicing=delivery, expense=sales_price'},
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
                'qty_delivered': 2.0,
                'product_uom_qty': 2.0,
                'is_expense': True,
            },
        ])
