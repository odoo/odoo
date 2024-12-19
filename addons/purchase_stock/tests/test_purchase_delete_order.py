# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command
from .common import PurchaseTestCommon


class TestDeleteOrder(PurchaseTestCommon):

    def test_00_delete_order(self):
        ''' Testcase for deleting purchase order with purchase user group'''

        # In order to test delete process on purchase order,tried to delete a confirmed order and check Error Message.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'state': 'purchase',
        })
        purchase_order_1 = purchase_order.with_user(self.res_users_purchase_user)
        with self.assertRaises(UserError):
            purchase_order_1.unlink()

        # Delete 'cancelled' purchase order with user group
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'state': 'purchase',
        })
        purchase_order_2 = purchase_order.with_user(self.res_users_purchase_user)
        purchase_order_2.button_cancel()
        self.assertEqual(purchase_order_2.state, 'cancel', 'PO is cancelled!')
        purchase_order_2.unlink()

        # Delete 'draft' purchase order with user group
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'state': 'draft',
        })
        purchase_order_3 = purchase_order.with_user(self.res_users_purchase_user)
        purchase_order_3.button_cancel()
        self.assertEqual(purchase_order_3.state, 'cancel', 'PO is cancelled!')
        purchase_order_3.unlink()

    def test_01_delete_propagation(self):
        ''' Testcase for deleting purchase order with linked move and propagate cancel off'''

        move = self.env['stock.move'].create({
            'name': self.product_2.name,
            'product_id': self.product_2.id,
            'product_uom_qty': 1,
            'product_uom': self.product_2.uom_id.id,
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.picking_type_out.id,
        })
        move._action_confirm()
        self.assertEqual(move.state, 'confirmed', 'Move should be confirmed as there is no quantity in stock')

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product_2.uom_id.id,
                    'propagate_cancel': False,
                })],
        })
        purchase_order.button_confirm()

        self.env['report.stock.report_reception'].action_assign(move.ids, [1], purchase_order.order_line.move_ids.ids)
        self.assertEqual(move.state, 'waiting', 'Move should be waiting for the linked purchase')
        purchase_order.button_cancel()
        # Check purchase order and related move are canceled while linked move state is not
        self.assertEqual(purchase_order.state, 'cancel', 'Purchase Order should be canceled')
        self.assertEqual(purchase_order.order_line.move_ids.state, 'cancel', 'Purchase order move should be canceled')
        self.assertEqual(move.state, 'confirmed', 'Move state should be recomputed to confimed')
