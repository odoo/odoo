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
        prod_order = self.env['product.product'].create({
           'name': "Zed+ Antivirus",
           'standard_price': 235.0,
           'list_price': 280.0,
           'type': 'consu',
           'invoice_policy': 'order',
           'uom_id': self.env.ref('product.product_uom_unit').id,
           'uom_po_id': self.env.ref('product.product_uom_unit').id,
        })
        prod_del = self.env['product.product'].create({
           'name': "Switch, 24 ports",
           'standard_price': 55.0,
           'list_price': 70.0,
           'type': 'consu',
           'invoice_policy': 'delivery',
           'uom_id': self.env.ref('product.product_uom_unit').id,
           'uom_po_id': self.env.ref('product.product_uom_unit').id,
        })
        serv_order = self.env['product.product'].create({
           'name': "Prepaid Consulting",
           'standard_price': 40.0,
           'list_price': 90.0,
           'type': 'service',
           'invoice_policy': 'order',
           'uom_id': self.env.ref('product.product_uom_hour').id,
           'uom_po_id': self.env.ref('product.product_uom_hour').id,
        })
        serv_del = self.env['product.product'].create({
           'name': "Cost-plus Contract",
           'standard_price': 200.0,
           'list_price': 180.0,
           'type': 'service',
           'invoice_policy': 'delivery',
           'uom_id': self.env.ref('product.product_uom_unit').id,
           'uom_po_id': self.env.ref('product.product_uom_unit').id,
        })        
        self.products = {
            'prod_order': prod_order,
            'prod_del': prod_del,
            'serv_order': serv_order,
            'serv_del': serv_del,
        }

        self.partner = self.env['res.partner'].create({
            'name': "Hugh Li"
        })

        self.deposit = self.env['product.product'].create({
            'name': "Deposit",
            'standard_price': 100,
            'list_price': 150,
            'type':'service',
            'invoice_policy': 'order',
        })
