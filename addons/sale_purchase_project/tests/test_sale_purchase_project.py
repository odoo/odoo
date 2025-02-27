# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_purchase.tests.test_sale_purchase import TestSalePurchase


@tagged('-at_install', 'post_install')
class TestSalePurchaseProject(TestSalePurchase):

    def test_pol_analytic_distribution(self):
        """Confirming SO, analytic accounts from the project's SO should be set as Analytic Distribution in POL."""
        self.env.user.group_ids += self.quick_ref('project.group_project_manager')
        project = self.env['project.project'].create({
            'name': 'SO Project',
            self.analytic_plan._column_name(): self.test_analytic_account_1.id,
        })
        # Remove the analytic account auto-generated when creating a timesheetable project if it exists
        project.account_id = False

        (self.sale_order_1 + self.sale_order_2).project_id = project
        self.sale_order_2.order_line.analytic_distribution = {str(self.test_analytic_account_2.id): 100}

        (self.sale_order_1 + self.sale_order_2).action_confirm()

        purchase_order = self.env['purchase.order'].search([('partner_id', '=', self.service_purchase_1.seller_ids.partner_id.id), ('state', '=', 'draft')])
        self.assertEqual(len(purchase_order), 2, "Two PO should have been created, from the 2 Sales orders")
        self.assertEqual(len(purchase_order.order_line), 2, "The purchase order should have 2 lines")
        self.assertEqual(set(purchase_order.mapped('state')), {'draft'}, "The created PO should be in draft state.")

        purchase_lines_so1 = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_1.order_line.ids)])
        self.assertEqual(len(purchase_lines_so1), 1, "Only one SO line from SO 1 should have create a PO line")
        purchase_line1 = purchase_lines_so1[0]

        purchase_lines_so2 = self.env['purchase.order.line'].search([('sale_line_id', 'in', self.sale_order_2.order_line.ids)])
        self.assertEqual(len(purchase_lines_so2), 1, "Only one SO line from SO 2 should have create a PO line")
        purchase_line2 = purchase_lines_so2[0]

        self.assertNotEqual(purchase_line1.product_id, purchase_line2.product_id, "The 2 PO line should have different products")
        self.assertEqual(purchase_line1.product_id, self.sol1_service_purchase_1.product_id, "The create PO line must have the same product as its mother SO line")
        self.assertEqual(purchase_line2.product_id, self.sol2_service_purchase_2.product_id, "The create PO line must have the same product as its mother SO line")

        self.assertEqual(purchase_line1.analytic_distribution, {str(self.sale_order_1.project_id[self.analytic_plan._column_name()].id): 100}, "Analytic Distribution in PO should be same as Analytic Account set in SO")
        self.assertEqual(purchase_line2.analytic_distribution, {str(self.test_analytic_account_2.id): 100}, "Analytic Distribution in PO should be same as Analytic Distribution set in SOL")
