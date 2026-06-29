# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.addons.sale_purchase.tests.common import TestCommonSalePurchaseNoChart
from odoo.tests import tagged, Form


@tagged('-at_install', 'post_install')
class TestAccessRights(TestCommonSalePurchaseNoChart):

    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a users
        group_sale_user = cls.env.ref('sales_team.group_sale_salesman')
        group_purchase_user = cls.env.ref('purchase.group_purchase_user')
        cls.user_salesperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Le Grand Jojo User',
            'login': 'grand.jojo',
            'email': 'grand.jojo@chansonbelge.com',
            'group_ids': [(6, 0, [group_sale_user.id])]
        })
        cls.user_purchaseperson = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Jean-Luc Fonck',
            'login': 'jl.fonck',
            'email': 'jl.fonck@chansonbelge.com',
            'group_ids': [(6, 0, [group_purchase_user.id])]
        })

    def test_access_saleperson(self):
        """ Check a saleperson (only) can generate a PO and a PO user can not confirm a SO """
        SaleOrder = self.env['sale.order']

        sale_order = SaleOrder.with_user(self.user_salesperson).create({
            'partner_id': self.partner_a.id,
            'user_id': self.user_salesperson.id
        })

        sol_service_purchase = self.env['sale.order.line'].with_user(self.user_salesperson).create({
            'product_id': self.service_purchase_1.id,
            'product_uom_qty': 4,
            'order_id': sale_order.id,
            'tax_ids': False,
        })

        # confirming SO will create the PO even if you don't have the rights
        sale_order.action_confirm()
        sale_order._action_cancel()

        self.assertTrue(sale_order.name, "Saleperson can read its own SO")

        action = sale_order.sudo().action_view_purchase_orders()

        # try to access PO as sale person
        with self.assertRaises(AccessError):
            purchase_orders = self.env['purchase.order'].with_user(self.user_salesperson).browse(action['res_id'])
            purchase_orders.read()

        # try to access PO as purchase person
        purchase_orders = self.env['purchase.order'].with_user(self.user_purchaseperson).browse(action['res_id'])
        purchase_orders.read()

        # try to access the PO lines from the SO, as sale person
        self.assertFalse(sol_service_purchase.with_user(self.user_salesperson).purchase_line_ids)
        with self.assertRaises(AccessError):
            sol_service_purchase.sudo().purchase_line_ids.with_user(self.user_salesperson).read()

    def test_access_forecasted_ministock(self):
        """ Test that a sale user can access a product without purchase rights
        and that a purchase user can access a product without sale rights. """
        if self.env["ir.module.module"]._get('stock').state == 'installed':
            self.skipTest("This test is only for stock without stock")

        with Form(self.product_a.with_user(self.user_salesperson)) as form_a_sale:
            # The free_qty field itself is not very important here. We just check that
            # we can read it, so there were no access errors.
            self.assertEqual(form_a_sale.free_qty, 0.0)
        with Form(self.product_a.with_user(self.user_purchaseperson)) as form_a_purchase:
            # The free_qty field itself is not very important here. We just check that
            # we can read it, so there were no access errors.
            self.assertEqual(form_a_purchase.free_qty, 0.0)
