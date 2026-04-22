# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleExpense(TestExpenseCommon, TestSaleCommon):

    def test_analytic_account_reinvoice_policy(self):
        product_form = Form(self.product_a.product_tmpl_id)
        product_form.can_be_expensed = True
        product_form.reinvoice_policy = 'cost'
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
        """ Test that the analytic distibution is well computed when we link a sale order to an expense """

        # Make sure the user has access to analytic accounting, otherwise the 'analytic_distribution' field will not appear
        # in the view and will not be computed
        self.env.user.write({'group_ids': [Command.link(self.env.ref('analytic.group_analytic_accounting').id)]})
        # Set the expense policy to 'sales_price' to make the 'sale_order_id' field visible on the form view
        self.product_c.reinvoice_policy = 'sales_price'

        self.analytic_plan_2 = self.env['account.analytic.plan'].create({'name': 'Other Plan Test'})
        self.analytic_account_3 = self.env['account.analytic.account'].create({
            'name': 'analytic_account_3',
            'plan_id': self.analytic_plan_2.id,
        })

        # Project Will use another analytic plan than the product
        project = self.env['project.project'].sudo().create({'name': 'SO Project'})
        project.account_id = self.analytic_account_3

        # Set an analytic distribution using account_1 on the product that will be used on the expense
        self.env['account.analytic.distribution.model'].create([{
            'product_id': self.product_c.id,
            'analytic_distribution': {str(self.analytic_account_1.id): 100}
        }])

        so_values = {
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product_c.name,
                'product_id': self.product_c.id,
                'product_uom_qty': 2,
                'price_unit': self.product_c.list_price,
            })],
            'project_id': project.id,
        }
        so1 = self.env['sale.order'].create(so_values)
        expense = self.create_expenses({
            'name': 'Expense Test',
            'sale_order_id': so1.id,
            'product_id': self.product_c.id,
        })

        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account_1.id): 100, str(self.analytic_account_3.id): 100},
            "The analytic distribution of the expense should be set to the account of the project and the one from the sale order.",
        )

        # Check that it default to the one from the sale order if the project has no analytic distribution
        project.account_id = False
        so2 = self.env['sale.order'].create(so_values)

        # We use the form to trigger the onchange on sale_order_id, which adds the 'analytic_distribution' field to the fields to recompute
        with Form(expense) as exp_form:
            exp_form.sale_order_id = so2

        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account_1.id): 100},
            "The analytic distribution of the expense should be the one from the sale order only",
        )

        # The analytic_account_2 has the same plan as the one from the sale order
        project.account_id = self.analytic_account_2
        so3 = self.env['sale.order'].create(so_values)
        with Form(expense) as exp_form:
            exp_form.sale_order_id = so3
        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account_2.id): 100},
            "The analytic distribution of the expense should keep only the one from the project when the so and project share the same plan",
        )

    def test_change_product_reinvoice_policy_analytic_distribution(self):
        """ Test that analytic distribution is not recomputed when changing the expense policy of the expense product """
        analytic_account_2 = self.analytic_account_1.copy()
        self.product_a.reinvoice_policy = 'sales_price'
        distribution_model = self.env['account.analytic.distribution.model'].create({
            'account_prefix': self.company_data['default_account_expense'].code,
            'analytic_distribution': {self.analytic_account_1.id: 100.0},
        })
        expenses = self.env['hr.expense'].create([
            {
                'name': f'Expense {i}',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
            } for i in range(1, 3)
        ])
        self.assertRecordValues(expenses, [
            {
                'account_id': self.company_data['default_account_expense'].id,
                'analytic_distribution': {str(self.analytic_account_1.id): 100.0},
            },
            {
                'account_id': self.company_data['default_account_expense'].id,
                'analytic_distribution': {str(self.analytic_account_1.id): 100.0},
            },
        ])

        distribution_model.analytic_distribution = {analytic_account_2.id: 100.0}
        expenses |= self.env['hr.expense'].create({
            'name': 'Expense 3',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
        })

        self.product_a.reinvoice_policy = 'cost'

        self.assertRecordValues(expenses, [
            {
                'analytic_distribution': {str(self.analytic_account_1.id): 100.0},
            },
            {
                'analytic_distribution': {str(self.analytic_account_1.id): 100.0},
            },
            {
                'analytic_distribution': {str(analytic_account_2.id): 100.0},
            },
        ])

    def test_aal_category_expense(self):
        """ This test ensures that when an expense generate an aal, its category and billable type are correctly set. """
        expensed_product = self.env['product.product'].create({
            'name': 'test product',
            'can_be_expensed': True,
            'type': 'service',
            'invoice_policy': 'order',
            'standard_price': 100,
            'reinvoice_policy': 'cost',
        })

        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        account = self.env['account.analytic.account'].create({
            'plan_id': project_plan.id,
            'name': 'Project account',
        })
        project = self.env['project.project'].sudo().create({'name': 'SO Project', 'account_id': account.id})
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_b.id})],
            'project_id': project.id,
        })
        sale_order.action_confirm()
        sale_order._create_invoices()

        expense = self.create_expenses({
            'product_id': expensed_product.id,
            'quantity': 1000.00,
            'analytic_distribution': {account.id: 100},
            'sale_order_id': sale_order.id,
        })
        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)

        line = self.env['account.analytic.line'].search([('account_id', '=', account.id)])
        self.assertEqual('expense', line.category)
        self.assertEqual('costs', line.category_report)
        self.assertEqual('13_expense', line.billable_type)
