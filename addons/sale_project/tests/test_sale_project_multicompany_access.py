from odoo.tests import TransactionCase
from odoo.tests import Form


class TestSaleOrderAccess(TransactionCase):

    def setUp(self):

        self.company_1 = self.env['res.company'].create({
            'name': 'Company 1',
            'currency_id': self.env.ref('base.USD').id,
        })
        self.company_2 = self.env['res.company'].create({
            'name': 'Company 2',
            'currency_id': self.env.ref('base.EUR').id,
        })
        self.user_company_1 = self.env['res.users'].create({
            'name': 'User 1',
            'login': 'user1',
            'password': 'password',
            'company_ids': [(6, 0, [self.company_1.id])],
            'company_id': self.company_1.id,
            'group_ids': [(6, 0, [
                self.env.ref('sales_team.group_sale_manager').id,
                self.env.ref('project.group_project_manager').id,
            ])]
        })
        self.admin_user = self.env['res.users'].create({
            'name': 'Admin User',
            'login': 'adminn',
            'password': 'password',
            'company_ids': [(6, 0, [self.company_1.id, self.company_2.id])],
            'company_id': self.company_1.id,
            'group_ids': [(6, 0, [
                self.env.ref('sales_team.group_sale_manager').id,
                self.env.ref('project.group_project_manager').id,
            ])],
            })
        self.partner = self.env['res.partner'].create({
            'name': 'XYZ',
            'type': 'contact'
        })
        self.project_company_2 = self.env['project.project'].create({
            'name': 'Project Company 2',
            'user_id': self.admin_user.id,
            'company_id': self.company_2.id,
            'partner_id': self.partner.id,
            'allow_billable': True,
        })
        self.sale_order_company_1 = self.env['sale.order'].create({
            'user_id': self.admin_user.id,
            'partner_id': self.partner.id,
            'company_id': self.company_1.id,
            'state': 'sale',
            'project_id': self.project_company_2.id
        })
        self.sale_line = self.env['sale.order.line'].create({
            'name': 'XA',
            'product_uom_qty': 1.00,
            'price_unit': 20.00,
            'order_id': self.sale_order_company_1.id,
            'project_id': self.project_company_2.id,
        })
        self.project_company_2.write({
            'sale_order_id': self.sale_order_company_1.id,
            'sale_line_id': self.sale_line.id,
        })

    def test_user_with_company_1_access_can_open_sale_order(self):
        Form(self.sale_order_company_1.with_user(self.admin_user).with_company(self.company_1))
        Form(self.sale_order_company_1.with_user(self.user_company_1).with_company(self.company_1))
