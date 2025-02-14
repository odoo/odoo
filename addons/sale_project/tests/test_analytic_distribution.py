# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleProjectCommon
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestAnalyticDistribution(HttpCase, TestSaleProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()
        cls.company_2 = cls.company_data_2['company']
        # Creating analytic plans within tests could cause some registry issues
        # hence we are creating them in the setupClass instead.
        # This is because creating a plan creates fields and columns on models inheriting
        # from the mixin.
        # The registry is reset on class cleanup.
        cls.plan_b = cls.env['account.analytic.plan'].create({'name': 'Q'})

        cls.analytic_account_sale_company_2 = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet - AA',
            'code': 'AA-4030',
            'plan_id': cls.analytic_plan.id,
            'company_id': cls.company_2.id,
        })
        cls.project_global_2 = cls.env["project.project"].create({
            'name': 'Project Global 2',
            'account_id': cls.analytic_account_sale.id,
            'allow_billable': True,
        })
        cls.product_delivery_manual2.with_company(cls.company_2).write({
            'project_id': cls.project_global_2,
        })

    def test_project_transmits_analytic_plans_to_sol_distribution(self):
        plan_a = self.analytic_plan
        plan_b = self.plan_b
        account_a, account_b = self.env['account.analytic.account'].create([{
            'name': 'account',
            'plan_id': plan.id,
        } for plan in (plan_a, plan_b)])
        project = self.env['project.project'].create({
            'name': 'X',
            plan_a._column_name(): account_a.id,
            plan_b._column_name(): account_b.id,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'project_id': project.id,
        })
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product.id,
        })
        self.assertEqual(
            sale_order_line.analytic_distribution,
            {f'{account_a.id},{account_b.id}': 100},
            "The sale order line's analytic distribution should have one line containing all the accounts of the project's plans"
        )

    def test_sol_analytic_distribution_project_template_service(self):
        sale_order = self.env['sale.order'].create({'partner_id': self.partner.id})
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_delivery_manual5.id,
        })
        self.assertFalse(
            sale_order_line.analytic_distribution,
            "No default analytic distribution should be set on the SOL as no project is linked to the SO, and we do not "
            "take the project template set on the product into account.",
        )
        sale_order.action_confirm()
        self.assertEqual(
            sale_order_line.analytic_distribution,
            {str(sale_order.project_id.account_id.id): 100},
            "The analytic distribution of the SOL should be set to the account of the generated project.",
        )

    def test_sol_analytic_distribution_task_in_project_service(self):
        self.project_global.account_id = self.analytic_account_sale
        sale_order = self.env['sale.order'].create({'partner_id': self.partner.id})
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_delivery_manual2.id,
        })
        self.assertEqual(
            sale_order_line.analytic_distribution,
            {str(self.project_global.account_id.id): 100},
            "The analytic distribution of the SOL should be set to the account of the project set on the product.",
        )

    def test_sol_analytic_distribution_task_in_project_service_multicompany(self):
        self.project_global.account_id = self.analytic_account_sale
        self.project_global_2.account_id = self.analytic_account_sale_company_2
        # Create an order for company_2 while the user's current company is company 1
        self.assertEqual(self.env.company, self.company)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.company_2.id,
        })
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_delivery_manual2.id,
        })
        self.assertEqual(
            sale_order_line.analytic_distribution,
            {str(self.project_global_2.account_id.id): 100},
            "The analytic distribution of the SOL should be set to the account of the project "
            "set on the product for the order's company",
        )
