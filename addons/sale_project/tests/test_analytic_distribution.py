# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleProjectCommon
from odoo import Command
from odoo.tests import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestAnalyticDistribution(HttpCase, TestSaleProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Creating analytic plans within tests could cause some registry issues
        # hence we are creating them in the setupClass instead.
        # This is because creating a plan creates fields and columns on models inheriting
        # from the mixin.
        # The registry is reset on class cleanup.
        cls.plan_b = cls.env['account.analytic.plan'].create({'name': 'Q'})

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

    def test_project_analytic_distribution_on_invoice_lines(self):
        """
        Test that Analytic Distribution applies from Project to Invoice Lines (excluding payable/receivable lines).
        Steps:
          1. Create a project.
          2. Create an invoice with the project in context.
          3. Add an invoice line.
          4. Verify analytic distribution is applied.
        """

        invoice = self.env['account.move'].with_context({
            'default_move_type': 'out_invoice',
            'default_partner_id': self.project_global.partner_id.id,
            'project_id': self.project_global.id
        }).create({
            'invoice_line_ids': [Command.create({
                'product_id': self.product_delivery_manual1.id,
                'quantity': 1,
                'price_unit': 10,
            })]
        })

        filtered_lines = invoice.line_ids.filtered(lambda l: l.analytic_distribution)
        self.assertEqual(
            len(filtered_lines),
            1,
            "Analytic distribution is not set on the payable/receivable lines"
        )

    def test_get_so_mapping_domain_with_no_analytic_distribution(self):
        """
        Ensure _get_so_mapping_domain doesnt fail when analytic_distribution is not set
        """

        account = self.env['account.account'].create({
            'name': 'Receivable test account',
            'code': '00001',
            'account_type': 'asset_receivable',
        })

        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
        })

        line = self.env['account.move.line'].create({
            'move_id': move.id,
            'name': 'Line without analytic',
            'quantity': 1,
            'price_unit': 100,
            'account_id': account.id,
        })
        domain = line._get_so_mapping_domain()

        self.assertEqual(
            domain,
            [(0, '=', 1)],
            "Domain should be (0, '=', 1) when analytic_distribution is missing."
        )
