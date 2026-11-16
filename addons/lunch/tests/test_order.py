# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, new_test_user
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

    def test_wallet_balance_keeps_sent_orders(self):
        order = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
        })
        Cashmove = self.env['lunch.cashmove']
        balance = Cashmove.get_wallet_balance(self.env.user, include_config=False)
        order.action_order()
        ordered_balance = Cashmove.get_wallet_balance(self.env.user, include_config=False)
        self.assertAlmostEqual(ordered_balance, balance - order.price)
        order.action_send()
        self.env.flush_all()
        self.assertAlmostEqual(Cashmove.get_wallet_balance(self.env.user, include_config=False), ordered_balance)
        order.action_confirm()
        self.env.flush_all()
        self.assertAlmostEqual(Cashmove.get_wallet_balance(self.env.user, include_config=False), ordered_balance)

    def test_cashmove_report_own_moves_only(self):
        user = new_test_user(self.env, 'lunch-user-report', 'base.group_user,lunch.group_lunch_user')
        self.env['lunch.cashmove'].create([
            {'user_id': user.id, 'amount': 10, 'description': 'mine'},
            {'user_id': self.manager.id, 'amount': 20, 'description': 'not mine'},
        ])
        Report = self.env['lunch.cashmove.report']
        self.assertEqual(Report.with_user(user).search([]).mapped('description'), ['mine'])
        self.assertEqual(self.env['lunch.cashmove'].with_user(user).get_wallet_balance(user, include_config=False), 10)
        self.assertLessEqual(
            {'mine', 'not mine'},
            set(Report.with_user(self.manager).search([('user_id', 'in', (user | self.manager).ids)]).mapped('description')))

    def test_order_manager_actions_bindings(self):
        # like their buttons, cancelling the meals and notifying their users is for the lunch managers
        user = new_test_user(self.env, 'lunch-user-actions', 'base.group_user,lunch.group_lunch_user')
        manager_actions = (
            self.env.ref('lunch.lunch_order_action_cancel') | self.env.ref('lunch.lunch_order_action_notify'))
        for action_user, visible in ((user, False), (self.manager, True)):
            bindings = self.env['ir.actions.actions'].with_user(action_user).get_bindings('lunch.order')
            bound_ids = {action['id'] for action in bindings.get('action', [])}
            self.assertEqual(bound_ids & set(manager_actions.ids), set(manager_actions.ids) if visible else set())
            self.assertIn(self.env.ref('lunch.lunch_order_action_confirm').id, bound_ids)
