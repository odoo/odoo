# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.sale_purchase.tests.test_sale_purchase import TestSalePurchase
from odoo.addons.sale_project.tests.test_reinvoice import TestReInvoice


@tagged('-at_install', 'post_install')
class TestSalePurchaseProject(TestSalePurchase, TestReInvoice):

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

    def test_purchase_order_reinvoiced_so_count(self):
        serv_cost = self.env['product.product'].create({
            'name': "Ordered at cost",
            'standard_price': 160,
            'list_price': 180,
            'type': 'consu',
            'invoice_policy': 'order',
            'expense_policy': 'cost',
            'default_code': 'PROD_COST',
            'service_type': 'manual',
        })
        project = self.env['project.project'].create({
            'name': 'SO Project',
            self.analytic_plan._column_name(): self.test_analytic_account_1.id,
        })
        self.sale_order.project_id = project
        self.sale_order.action_confirm()

        purchase_order = self.env['purchase.order'].create({
            'name': 'PO Project',
            'partner_id': self.partner_a.id,
            'project_id': project.id,
            'order_line': [
                Command.create({
                    'product_id': serv_cost.id,
                    'product_qty': 2,
                })
            ]
        })
        purchase_order.button_confirm()
        purchase_order.order_line.qty_received = 2
        purchase_order.action_create_invoice()

        invoice = purchase_order.invoice_ids
        invoice.invoice_date = self.sale_order.date_order
        invoice.action_post()
        self.assertEqual(
            invoice.invoice_line_ids.reinvoiced_sale_line_id,
            self.sale_order.order_line,
            "The generated SO line should be linked to the invoice line from which it was reinvoiced.",
        )
        self.assertEqual(
            purchase_order.reinvoiced_so_count,
            1,
            "There should be exactly one SO from which a reinvoicing was done from the purchase orders's bills.",
        )
