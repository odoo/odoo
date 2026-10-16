# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common
from odoo.addons.lunch.tests.common import TestsCommon


class TestOrder(TestsCommon):

    def test_available_toppings_batch(self):
        self.env['lunch.topping'].create([
            {'name': 'Second extra', 'price': 1, 'supplier_id': self.supplier_pizza_inn.id, 'topping_category': 1},
            {'name': 'Drink', 'price': 2, 'supplier_id': self.supplier_pizza_inn.id, 'topping_category': 3},
            {'name': 'Unassigned', 'price': 3, 'topping_category': 2},
            {'name': 'Other supplier', 'price': 4, 'supplier_id': self.supplier_kothai.id, 'topping_category': 2},
        ])
        orders = self.env['lunch.order'].create([
            {'product_id': product.id, 'note': str(index)}
            for index, product in enumerate(self.product_pizza | self.product_sandwich_tuna)
        ])
        orders |= orders[:1].copy({'note': 'Another pizza'})
        orders._compute_available_toppings()
        with self.assertQueryCount(1):
            orders._compute_available_toppings()
        self.assertRecordValues(orders, [
            {'available_toppings_1': True, 'available_toppings_2': False, 'available_toppings_3': True},
            {'available_toppings_1': False, 'available_toppings_2': False, 'available_toppings_3': False},
            {'available_toppings_1': True, 'available_toppings_2': False, 'available_toppings_3': True},
        ])
        # Onchange records without a supplier must still find unassigned toppings.
        order = self.env['lunch.order'].new({})
        self.assertRecordValues(order, [
            {'available_toppings_1': False, 'available_toppings_2': True, 'available_toppings_3': False},
        ])
        self.env['lunch.order']._compute_available_toppings()

    def test_available_toppings_record_rule(self):
        self.env['ir.access'].create({
            'name': 'Hide olives',
            'model_id': self.env['ir.model']._get_id('lunch.topping'),
            'operation': 'r',
            'domain': [('id', '!=', self.topping_olives.id)],
        })
        order = self.env['lunch.order'].with_user(self.manager).new({'product_id': self.product_pizza.id})
        self.assertRecordValues(order, [
            {'available_toppings_1': False, 'available_toppings_2': False, 'available_toppings_3': False},
        ])

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
