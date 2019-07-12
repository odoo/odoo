# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart


class TestAccessRights(TestCommonSalePurchaseNoChart):

    @classmethod
    def setUpClass(cls):
        super(TestAccessRights, cls).setUpClass()

        cls.setUpServicePurchaseProducts()

        # Create a users
        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        cls.user_salesperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Le Grand Jojo User',
            'login': 'grand.jojo',
            'email': 'grand.jojo@chansonbelge.com',
            'groups_id': [(6, 0, [group_sale_user.id])]
        })
        cls.user_purchaseperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Jean-Luc Fonck',
            'login': 'jl.fonck',
            'email': 'jl.fonck@chansonbelge.com',
            'groups_id': [(6, 0, [group_purchase_user.id])]
        })

    def test_access_saleperson(self):
        """ Check a saleperson (only) can generate a PO and a PO user can not confirm a SO """
        SaleOrder = self.env['sale.order'].with_context(tracking_disable=True)

        sale_order = SaleOrder.with_user(self.user_salesperson).create({
            'partner_id': self.partner_customer_usd.id,
            'user_id': self.user_salesperson.id
        })

        sol_service_purchase = self.env['sale.order.line'].with_user(self.user_salesperson).create({
            'name': self.service_purchase_1.name,
            'product_id': self.service_purchase_1.id,
            'product_uom_qty': 4,
            'product_uom': self.service_purchase_1.uom_id.id,
            'price_unit': self.service_purchase_1.list_price,
            'order_id': sale_order.id,
            'tax_id': False,
        })

        # confirming SO will create the PO even if you don't have the rights
        sale_order.action_confirm()
        sale_order.action_cancel()

        self.assertTrue(sale_order.name, "Saleperson can read its own SO")

        action = sale_order.sudo().action_view_purchase()

        # try to access PO as sale person
        with self.assertRaises(AccessError):
            purchase_orders = self.env['purchase.order'].with_user(self.user_salesperson).search(action['domain'])
            purchase_orders.read()

        # try to access PO as purchase person
        purchase_orders = self.env['purchase.order'].with_user(self.user_purchaseperson).search(action['domain'])
        purchase_orders.read()

        # try to access the PO lines from the SO, as sale person
        with self.assertRaises(AccessError):
            sol_service_purchase.with_user(self.user_salesperson).purchase_line_ids.read()
