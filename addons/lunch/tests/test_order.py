# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.lunch.tests.common import TestsCommon


class TestOrder(TestsCommon):

    @common.users('cle-lunch-manager')
    def test_create_only_updates_new_orders(self):
        """
        Test that creating a new order only increments quantity for orders
        in 'new' state, not 'ordered'.
        """
        order_ordered = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
        })
        order_ordered.action_order()
        self.assertEqual(order_ordered.state, 'ordered')
        self.assertEqual(order_ordered.quantity, 1)

        order_new = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
        })
        self.assertEqual(order_new.state, 'new')
        self.assertEqual(order_new.quantity, 1)

        self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
        })

        self.assertEqual(order_new.quantity, 2, "New order should be incremented")
        self.assertEqual(order_ordered.quantity, 1, "Ordered order should NOT be incremented")
