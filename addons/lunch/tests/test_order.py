# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.addons.lunch.tests.common import TestsCommon


class TestOrder(TestsCommon):

    def test_reorder_respects_wallet(self):
        balance = self.env['lunch.cashmove'].get_wallet_balance(self.env.user)

        # Ensure the wallet balance for the user is enough for one pizza
        self.env['lunch.cashmove'].create({
            'user_id': self.env.user.id,
            'amount': balance * -1 + self.product_pizza.price,
        })

        order_ordered = self.env['lunch.order'].create({
            'product_id': self.product_pizza.id,
            'user_id': self.env.user.id,
            'lunch_location_id': self.location_office_1.id,
            'quantity': 1,
        })

        order_ordered.action_order()

        with self.assertRaises(ValidationError):
            order_ordered.action_reorder()
