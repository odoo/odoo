# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestSale(AccountingTestCase):
    def setUp(self):
        super(TestSale, self).setUp()
        # some users
        group_manager = self.env.ref('sales_team.group_sale_manager')
        group_user = self.env.ref('sales_team.group_sale_salesman')
        self.manager = self.env['res.users'].create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'email': 'a.m@example.com',
            'signature': '--\nAndreww',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_manager.id])]
        })
        self.user = self.env['res.users'].create({
            'name': 'Mark User',
            'login': 'user',
            'email': 'm.u@example.com',
            'signature': '--\nMark',
            'notification_type': 'email',
            'groups_id': [(6, 0, [group_user.id])]
        })
        # create quotation with differend kinds of products (all possible combinations)
        self.products = {
            'prod_order': self.env.ref('product.product_order_01'),
            'prod_del': self.env.ref('product.product_delivery_01'),
            'serv_order': self.env.ref('product.service_order_01'),
            'serv_del': self.env.ref('product.service_delivery'),
        }

        self.partner = self.env.ref('base.res_partner_1')
