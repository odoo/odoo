# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.project_hr_expense.tests.test_project_profitability import TestProjectHrExpenseProfitabilityCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.sale_project.tests.test_project_profitability import TestProjectProfitabilityCommon


@tagged('-at_install', 'post_install')
class TestProjectSaleExpenseProfitability(TestProjectProfitabilityCommon, TestProjectHrExpenseProfitabilityCommon, TestSaleCommon):
    def test_project_profitability(self):
        expense = self.env['hr.expense'].create({
            'name': 'expense',
            'product_id': self.company_data['product_order_sales_price'].id,
            'unit_amount': self.company_data['product_order_sales_price'].list_price,
            'employee_id': self.expense_employee.id,
            'analytic_distribution': {self.project.analytic_account_id.id: 100},
            'sale_order_id': self.sale_order.id,
        })

        # See method definition in `project_hr_expense.tests.test_project_profitability`
        expense_sheet = self.check_project_profitability_before_creating_and_approving_expense_sheet(
            expense,
            self.project,
            self.project_profitability_items_empty)

        expense_profitability = self.project._get_expenses_profitability_items(False)
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': -280.0, 'to_bill': 0.0},
        )

        expense_sheet.action_sheet_move_create()

        self.assertRecordValues(self.sale_order.order_line, [
            # Original SO line:
            {
                'product_id': self.product_delivery_service.id,
                'qty_delivered': 0.0,
                'product_uom_qty': 10,
                'is_expense': False,
            },
            {
                'product_id': self.company_data['product_order_sales_price'].id,
                'qty_delivered': 1.0,
                'product_uom_qty': 1.0,
                'is_expense': True,
            },
        ])
        expense_sol = self.sale_order.order_line.filtered(lambda sol: sol.product_id == self.company_data['product_order_sales_price'])

        expense_profitability = self.project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol.untaxed_amount_to_invoice},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': -280.0, 'to_bill': 0.0},
        )

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'revenues': {
                    'data': [expense_profitability['revenues']],
                    'total': {k: v for k, v in expense_profitability['revenues'].items() if k in ['to_invoice', 'invoiced']},
                },
                'costs': {
                    'data': [expense_profitability['costs']],
                    'total': {k: v for k, v in expense_profitability['costs'].items() if k in ['to_bill', 'billed']},
                },
            }
        )

        invoice = self.env['sale.advance.payment.inv'] \
            .with_context({
                'active_model': 'sale.order',
                'active_id': self.sale_order.id,
            }).create({
                'advance_payment_method': 'delivered',
            })._create_invoices(self.sale_order)
        invoice.action_post()

        expense_profitability = self.project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': expense_sol.untaxed_amount_invoiced, 'to_invoice': 0.0},
        )

        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        expense_profitability = self.project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {'id': 'expenses', 'sequence': expense_sequence, 'invoiced': 0.0, 'to_invoice': expense_sol.untaxed_amount_to_invoice},
        )

        self.sale_order._action_cancel()
        expense_profitability = self.project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertDictEqual(
            expense_profitability['costs'],
            {'id': 'expenses', 'sequence': expense_sequence, 'billed': -280.0, 'to_bill': 0.0},
        )

        expense_sheet.refuse_sheet('Test Cancel Expense')
        expense_profitability = self.project._get_expenses_profitability_items(False)
        self.assertDictEqual(
            expense_profitability.get('revenues', {}),
            {},
        )
        self.assertDictEqual(
            expense_profitability.get('costs', {}),
            {},
        )
