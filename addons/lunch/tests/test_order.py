# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.lunch.tests.common import TestsCommon


class TestOrder(TestsCommon):

    @common.users('cle-lunch-manager')
    def test_order_not_self_archived_on_state_update(self):
        """
        Test that updating an order's state doesn't cause it to match itself
        and get archived (clicking "Receive" multiple times).
        """
        order = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
        })
        order.write({'state': 'confirmed'})
        order.write({'state': 'confirmed'})

        self.assertTrue(order.active)
        self.assertEqual(order.quantity, 1)

    @common.users('cle-lunch-manager')
    def test_orders_not_used_as_merge_targets(self):
        """
        Test that confirmed or sent orders are excluded from merge logic to prevent
        orders being archived without quantity updates.
        """
        order1 = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
            'note': 'Pizza',
        })
        order1.write({'state': 'confirmed'})

        order2 = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
            'note': 'Pizza',
        })

        self.assertTrue(order1.active)
        self.assertTrue(order2.active)
        self.assertEqual(order1.quantity, 1)
        self.assertEqual(order2.quantity, 1)
