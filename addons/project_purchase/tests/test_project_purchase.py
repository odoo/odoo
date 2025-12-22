# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.project_purchase.tests.test_project_profitability import TestProjectPurchaseProfitability


class TestProjectPurchase(TestProjectPurchaseProfitability):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.proj_analytic_account = cls.env['account.analytic.account'].create({
            'name': 'AA of Project',
            'plan_id': cls.project_plan.id,
        })
        cls.project1 = cls.env['project.project'].create({
            'name': 'Project',
            'account_id': cls.proj_analytic_account.id,
        })

        # Create additional analytic plans at setup to avoid adding fields in project.project between tests
        cls.analytic_plan_1 = cls.env['account.analytic.plan'].create({'name': 'Purchase Project Plan 1'})
        cls.analytic_plan_2 = cls.env['account.analytic.plan'].create({'name': 'Purchase Project Plan 2'})

    def test_project_on_pol_with_analytic_distribution_model(self):
        """ If a line has a distribution coming from an analytic distribution model, and the PO has a project,
            both the project account and the accounts from the ADM should still be in the line after confirmation.
            The Project account should appear on all lines if there are several Analytic Distribution Models applying.
        """
        # We create one distribution model with two accounts in one line, based on product
        # and a second model with a different plan, based on partner
        analytic_account_1 = self.env['account.analytic.account'].create({
            'name': 'Analytic Account - Plan 1',
            'plan_id': self.analytic_plan_1.id,
        })
        analytic_account_2 = self.env['account.analytic.account'].create({
            'name': 'Analytic Account - Plan 2',
            'plan_id': self.analytic_plan_2.id,
        })
        distribution_model_product = self.env['account.analytic.distribution.model'].create({
            'product_id': self.product_order.id,
            'analytic_distribution': {','.join([str(analytic_account_1.id), str(analytic_account_2.id)]): 100},
            'company_id': self.company.id,
        })
        distribution_model_partner = self.env['account.analytic.distribution.model'].create({
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account.id: 100},
            'company_id': self.company.id,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_order.id}),
            ],
        })
        self.assertEqual(
            purchase_order.order_line.analytic_distribution,
            distribution_model_product.analytic_distribution | distribution_model_partner.analytic_distribution
        )

        # When we add a project to the PO, it should keep the previous accounts + the project account
        purchase_order.project_id = self.project1
        expected_distribution_project = {
            f"{analytic_account_1.id},{analytic_account_2.id},{self.project1.account_id.id}": 100,
            f"{self.analytic_account.id},{self.project1.account_id.id}": 100,
        }
        self.assertEqual(purchase_order.order_line.analytic_distribution, expected_distribution_project)

    def test_compute_purchase_orders_count(self):
        self.project1.account_id = self.analytic_account  # Project with analytics
        order_line_values = {
            'product_id': self.product_order.id,
            'product_qty': 1,
            'price_unit': self.product_order.standard_price,
            'currency_id': self.env.company.currency_id.id,
        }
        self.env['purchase.order'].create([
            {
                'name': 'Purchase Order 1',
                'partner_id': self.partner_a.id,
                'order_line': [Command.create({**order_line_values, 'analytic_distribution': {self.analytic_account.id: 100}})]
            },
            {
                'name': 'Purchase Order 2',
                'partner_id': self.partner_a.id,
                'project_id': self.project1.id,
                'order_line': [Command.create(order_line_values)],
            },
            {
                'name': 'Purchase Order 3',
                'partner_id': self.partner_a.id,
                'project_id': self.project1.id,
                'order_line': [Command.create({**order_line_values, 'analytic_distribution': {self.analytic_account.id: 100}})]
            },
        ])
        self.assertEqual(self.project1.purchase_orders_count, 3, 'The number of purchase orders linked to project1 should be equal to 3.')

        project2 = self.env['project.project'].create({'name': 'Project'})
        project2.account_id = False  # Project without analytics
        self.env['purchase.order'].create([
            {
                'name': 'Purchase Order 4',
                'partner_id': self.partner_a.id,
                'project_id': project2.id,
                'order_line': [Command.create(order_line_values)],
            },
            {
                'name': 'Purchase Order 5',
                'partner_id': self.partner_a.id,
                'project_id': project2.id,
                'order_line': [Command.create(order_line_values)],
            },
        ])
        self.assertEqual(project2.purchase_orders_count, 2, 'The number of purchase orders linked to project2 should be equal to 2.')
