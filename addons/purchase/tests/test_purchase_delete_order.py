# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from .common import TestPurchase


class TestDeleteOrder(TestPurchase):

    def test_00_delete_order(self):
        ''' Testcase for deleting purchase order with purchase user group'''

        # In order to test delete process on purchase order,tried to delete a confirmed order and check Error Message.
        purchase_order_1 = self.env.ref('purchase.purchase_order_1').sudo(self.res_users_purchase_user.id)
        with self.assertRaises(UserError):
            purchase_order_1.unlink()

        # Delete 'cancelled' purchase order with user group
        purchase_order_7 = self.env.ref('purchase.purchase_order_7').sudo(self.res_users_purchase_user.id)
        purchase_order_7.button_cancel()
        self.assertEqual(purchase_order_7.state, 'cancel', 'PO is cancelled!')
        purchase_order_7.unlink()

        # Delete 'draft' purchase order with user group
        purchase_order_5 = self.env.ref('purchase.purchase_order_5').sudo(self.res_users_purchase_user.id)
        self.assertEqual(purchase_order_5.state, 'draft', 'PO in draft state!')
        purchase_order_5.button_cancel()
        self.assertEqual(purchase_order_5.state, 'cancel', 'PO is cancelled!')
        purchase_order_5.unlink()
