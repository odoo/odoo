# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from .common import PurchaseTestCommon


class TestDeleteOrder(PurchaseTestCommon):

    def test_00_delete_order(self):
        ''' Testcase for deleting purchase order with purchase user group'''

        # In order to test delete process on purchase order,tried to delete a confirmed order and check Error Message.
        partner = self.env['res.partner'].create({'name': 'My Partner'})

        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'state': 'purchase',
        })
        purchase_order_1 = purchase_order.with_user(self.res_users_purchase_user)
        with self.assertRaises(UserError):
            purchase_order_1.unlink()

        # Delete 'cancelled' purchase order with user group
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'state': 'purchase',
        })
        purchase_order_2 = purchase_order.with_user(self.res_users_purchase_user)
        purchase_order_2.button_cancel()
        self.assertEqual(purchase_order_2.state, 'cancel', 'PO is cancelled!')
        purchase_order_2.unlink()

        # Delete 'draft' purchase order with user group
        purchase_order = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'state': 'draft',
        })
        purchase_order_3 = purchase_order.with_user(self.res_users_purchase_user)
        purchase_order_3.button_cancel()
        self.assertEqual(purchase_order_3.state, 'cancel', 'PO is cancelled!')
        purchase_order_3.unlink()
