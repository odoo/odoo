# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from .common import TestPurchase


class TestDeleteOrder(TestPurchase):

    def test_00_delete_order(self):
        # Create a user as 'Purchase manager'
        purchase_user = self.env['res.users'].create({
            'company_id': self.env.ref('base.main_company').id,
            'name': "Purchase User",
            'login': "pu",
            'email': "purchaseuser@yourcompany.com",
            'groups_id': [(6, 0, [self.env.ref('purchase.group_purchase_user').id])],
        })

        # In order to test to delete process on purchase order, I try to delete confirmed order and check Error Message
        purchase_order_1 = self.env.ref('purchase.purchase_order_1').sudo(purchase_user.id)
        with self.assertRaises(UserError):
            purchase_order_1.unlink()

        # I delete a cancelled order
        purchase_order_7 = self.env.ref('purchase.purchase_order_7').sudo(purchase_user.id)
        purchase_order_7.button_cancel()
        self.assertEqual(purchase_order_7.state, 'cancel', 'PO is cancelled!')
        purchase_order_7.unlink()

        # I delete a draft order
        purchase_order_5 = self.env.ref('purchase.purchase_order_5').sudo(purchase_user.id)
        self.assertEqual(purchase_order_5.state, 'draft', 'PO in draft state!')
        purchase_order_5.button_cancel()
        self.assertEqual(purchase_order_5.state, 'cancel', 'PO is cancelled!')
        purchase_order_5.unlink()

        # In order to test the duplicate order and check duplicate details. I duplicate order.
        purchase_order_1.copy()
