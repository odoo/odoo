# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged("post_install", "-at_install")
class TestRewardLineDescription(TestSaleCouponCommon):
    """`name_short` shows the description of the reward, not the generic product.

    All discount and shipping rewards carry one generic product named "Discount". The base
    compute of `website_sale` names the line after its product, thus without the override the
    cart would show "Discount" for every reward.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.program = cls.env["loyalty.program"].create({
            "name": "Order discount",
            "program_type": "promotion",
            "applies_on": "current",
            "trigger": "auto",
            "rule_ids": [Command.create({"minimum_amount": 1})],
            "reward_ids": [
                Command.create({
                    "reward_type": "discount",
                    "discount": 10,
                    "discount_mode": "percent",
                    "discount_applicability": "order",
                })
            ],
        })
        cls.reward = cls.program.reward_ids

    def _claim_reward_line(self):
        """Put the reward of the program on a new order and give back its reward line."""
        order = self._create_so()
        order._update_programs_and_rewards()
        self._claim_reward(order, self.program)
        return order.order_line.filtered("is_reward_line")[:1]

    def test_name_short_shows_the_reward_description(self):
        line = self._claim_reward_line()
        self.assertEqual(line.name_short, self.reward.description)
        self.assertNotEqual(line.name_short, line.product_id.name)

    def test_name_short_follows_a_changed_discount(self):
        """Changing the discount recomputes the description; the line must follow."""
        line = self._claim_reward_line()
        self.reward.sudo().discount = 25
        self.assertEqual(line.name_short, self.reward.description)

    def test_free_product_reward_keeps_the_name_of_its_product(self):
        self.reward.sudo().write({
            "reward_type": "product",
            "reward_product_id": self.product.id,
            "reward_product_qty": 1,
        })
        self.assertEqual(
            self._claim_reward_line().name_short,
            self.product.with_context(display_default_code=False).display_name,
        )
