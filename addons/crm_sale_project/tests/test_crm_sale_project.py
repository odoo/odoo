from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.crm.tests.common import TestCrmCommon


@tagged('at_install', '-post_install')
class TestCrmSaleOrderProject(TestCrmCommon):

    def test_sale_order_project_opportunity_link(self):
        action = self.lead_1.action_create_project()
        projects = self.env['project.project'].with_context(action['context']).create([
            {'name': 'Project 1'},
            {'name': 'Project 2'},
        ])
        product = self.env['product.product'].create({
            'name': 'Test Rental Product',
        })
        partner = self.env['res.partner'].create({'name': 'test partner'})
        self.lead_1.partner_id = partner
        # user with out project access to generate a sales quotation
        self.user_sales_leads.group_ids -= (self.env.ref('project.group_project_user') + self.env.ref('project.group_project_manager'))
        sale_order_action = self.lead_1.with_user(self.user_sales_leads).action_sale_quotations_new()
        so1, so2 = self.env['sale.order'].with_context(sale_order_action['context']).create([{
            'partner_id': partner.id,
            'order_line': [Command.create({'product_id': product.id})],
        } for _dummy in range(2)])
        self.assertEqual(so1.project_id, projects[1], "Sale Order should be linked to recent project.")
        self.assertEqual(so2.project_id, projects[1], "Sale Order should be linked to recent project.")
        self.assertEqual(projects[0].reinvoiced_sale_order_id, so1, "Project should be linked to first sale order.")
        self.assertEqual(projects[1].reinvoiced_sale_order_id, so1, "Project should be linked to first sale order.")

    def test_project_links_sale_order_when_created_after_so(self):
        product = self.env['product.product'].create({
            'name': 'Test Rental Product',
        })
        partner = self.env['res.partner'].create({'name': 'test partner'})
        self.lead_1.partner_id = partner
        sale_order_action = self.lead_1.action_sale_quotations_new()
        sole_order = self.env['sale.order'].with_context(sale_order_action['context']).create({
            'partner_id': partner.id,
            'order_line': [Command.create({'product_id': product.id})],
        })
        action = self.lead_1.action_create_project()
        project = self.env['project.project'].with_context(action['context']).create({'name': 'Project 1'})
        self.assertEqual(project.reinvoiced_sale_order_id, sole_order, "Project should be linked to sale order.")
