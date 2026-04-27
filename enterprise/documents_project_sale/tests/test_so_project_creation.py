# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import tagged, new_test_user

from odoo.addons.sale_project.tests.common import TestSaleProjectCommon


@tagged("-at_install", "post_install")
class testSoProjectCreation(TestSaleProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_manager = new_test_user(cls.env, login='sale_manager', groups='sales_team.group_sale_manager')

        cls.use_documents_project_template, cls.project_template = cls.env['project.project'].create([{
            'name': 'Test Project',
        }, {
            'name': 'Template Project',
            'use_documents': False,
        }])

    def test_project_template_with_documents_disabled(self):
        product_template = self.env['product.template'].create({
            'name': 'Product 1',
            'type': 'service',
            'service_tracking': 'project_only',
            'project_template_id': self.project_template.id,
        })

        self.assertFalse(self.project_template.use_documents)

        product = self.env['product.product'].search([('product_tmpl_id', '=', product_template.id)])
        sales_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': product.id})],
        })
        sales_order.action_confirm()
        self.assertFalse(sales_order.project_ids.use_documents, "The generated project should have the documents feature disabled.")

    def test_workspace_from_project(self):
        """
            This tests the flow of creating a project and then using
            that project and its workplace to create the product
        """
        self.env['product.template'].create({
            'name': 'Test product',
            'type': 'service',
            'service_tracking': 'task_in_project',
            'project_template_id': self.use_documents_project_template.id,
        })

    def test_so_creation_without_template_only_sale_access_rights(self):
        sales_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_delivery_manual3.id})],
        })
        res = sales_order.with_user(self.sale_manager).action_confirm()
        self.assertTrue(res)

    def test_so_creation_with_template_only_sale_access_rights(self):
        self.product_delivery_manual3.project_template_id = self.use_documents_project_template.id
        sales_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_delivery_manual3.id})],
        })
        res = sales_order.with_user(self.sale_manager).action_confirm()
        self.assertTrue(res)
