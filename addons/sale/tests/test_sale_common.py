# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.addons.account.tests.account_test_classes import AccountingTestCase


class TestSale(AccountingTestCase):
    def setUp(self):
        super(TestSale, self).setUp()
        # some users
        group_manager = self.env.ref('base.group_sale_manager')
        group_user = self.env.ref('base.group_sale_salesman')
        self.manager = self.env['res.users'].create({
            'name': 'Andrew Manager',
            'login': 'manager',
            'alias_name': 'andrew',
            'email': 'a.m@example.com',
            'signature': '--\nAndreww',
            'notify_email': 'always',
            'groups_id': [(6, 0, [group_manager.id])]
        })
        self.user = self.env['res.users'].create({
            'name': 'Mark User',
            'login': 'user',
            'alias_name': 'mark',
            'email': 'm.u@example.com',
            'signature': '--\nMark',
            'notify_email': 'always',
            'groups_id': [(6, 0, [group_user.id])]
        })
        # create quotation with differend kinds of products (all possible combinations)
        self.products = {
            'prod_order': self.env.ref('product.product_product_43'),
            'prod_del': self.env.ref('product.product_product_47'),
            'serv_order': self.env.ref('product.product_product_0'),
            'serv_del': self.env.ref('product.product_product_56'),
        }

        self.partner = self.env.ref('base.res_partner_1')
