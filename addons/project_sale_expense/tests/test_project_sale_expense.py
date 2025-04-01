# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestExpenseCommon, TestSaleCommon):

    def test_analytic_account_expense_policy(self):
        product_form = Form(self.product_a.product_tmpl_id)
        product_form.can_be_expensed = True
        product_form.expense_policy = 'cost'
        product_form.can_be_expensed = False
        self.product_a.product_tmpl_id = product_form.save()

        project = self.env['project.project'].sudo().create({'name': 'SO Project'})
        # Remove the analytic account auto-generated when creating a timesheetable project if it exists
        project.account_id = False

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
                'price_unit': self.product_a.list_price,
            })],
            'project_id': project.id,
        })
        so.action_confirm()
        self.assertFalse(so.project_account_id)

    def test_compute_analytic_distribution_expense(self):
        project = self.env['project.project'].sudo().create({'name': 'SO Project'})
        project.account_id = self.analytic_account_1
        so_values = {
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
                'price_unit': self.product_a.list_price,
            })],
            'project_id': project.id,
        }

        so1 = self.env['sale.order'].create(so_values)
        expense = self.create_expenses({
            'name': 'Expense Test',
            'sale_order_id': so1.id,
        })
        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account_1.id): 100},
            "The analytic distribution of the expense should be set to the account of the project.",
        )

        project.account_id = False
        so2 = self.env['sale.order'].create(so_values)
        expense.sale_order_id = so2
        self.assertFalse(
            expense.analytic_distribution,
            "The analytic distribution of the expense should be unset as the project has no account.",
        )
