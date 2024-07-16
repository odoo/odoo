# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleProjectCommon
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestAnalyticDistribution(HttpCase, TestSaleProjectCommon):
    def test_project_transmits_analytic_plans_to_sol_distribution(self):
        AnalyticPlan = self.env['account.analytic.plan']
        plan_a = self.analytic_plan
        plan_b = AnalyticPlan.sudo().search([
            ('parent_id', '=', False),
            ('id', '!=', plan_a.id),
        ], limit=1)
        plan_b = plan_b or AnalyticPlan.create({'name': 'Q'})
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
