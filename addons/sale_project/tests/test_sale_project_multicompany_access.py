from odoo import Command
from odoo.tests import Form, TransactionCase


class TestSaleOrderAccess(TransactionCase):
    def test_user_with_company_1_access_can_open_sale_order(self):
        company_1, company_2 = self.env['res.company'].create([
            {"name": "Company 1 Sale Order"},
            {"name": "Company 2 Project"},
        ])
        user_company_1 = self.env['res.users'].create({
            'name': 'User 1',
            'login': 'user1',
            'password': 'password',
            'company_ids': [(6, 0, [company_1.id])],
            'company_id': company_1.id,
            'group_ids': [(6, 0, [
                self.env.ref('sales_team.group_sale_manager').id,
                self.env.ref('project.group_project_manager').id,
            ])]
        })
        admin_user = self.env['res.users'].create({
            'name': 'Admin User',
            'login': 'adminn',
            'password': 'password',
            'company_ids': [(6, 0, [company_1.id, company_2.id])],
            'company_id': company_1.id,
            'group_ids': [(6, 0, [
                self.env.ref('sales_team.group_sale_manager').id,
                self.env.ref('project.group_project_manager').id,
            ])],
            })
        partner = self.env['res.partner'].create({
            'name': 'XYZ',
            'type': 'contact'
        })
        product_order_service = self.env['product.product'].create({
            'name': "Service Ordered",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
        })
        project_company_2 = self.env['project.project'].create({
            'name': 'Project Company 2',
            'user_id': admin_user.id,
            'company_id': company_2.id,
            'partner_id': partner.id,
            'allow_billable': True,
        })
        sale_order_company_1 = self.env['sale.order'].create({
            'user_id': admin_user.id,
            'partner_id': partner.id,
            'company_id': company_1.id,
            'state': 'sale',
            'project_id': project_company_2.id,
            'order_line': [
                Command.create({
                    'product_id': product_order_service.id,
                    'product_uom_qty': 1,
                    'project_id':  project_company_2.id,
                }),
            ]
        })
        project_company_2.write({
            'sale_order_id': sale_order_company_1.id,
            'sale_line_id': sale_order_company_1.order_line.id
        })
        Form(sale_order_company_1.with_user(admin_user).with_company(company_1))
        Form(sale_order_company_1.with_user(user_company_1).with_company(company_1))
