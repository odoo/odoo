# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon


@tagged("post_install", "-at_install")
class TestSaleOrderInvoicingUserAccess(TestSaleCouponCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.invoicing_user = new_test_user(
            cls.env,
            login="test_invoicing_only_user",
            groups="base.group_user,account.group_account_invoice",
            name="Invoicing Only User",
        )

    def _order_with_gift_cards(self, quantity=2):
        order = self._create_so(
            order_line=[
                Command.create({
                    "product_id": self.product_gift_card.id,
                    "product_uom_qty": quantity,
                })
            ]
        )
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), quantity)
        return order

    def test_gift_card_count_not_readable_by_invoicing_user(self):
        order = self._order_with_gift_cards(quantity=2)
        # Start with a clean cache so the read below goes through the
        # invoicing user's own access rights instead of reusing a value
        # cached under another user.
        self.env.invalidate_all()
        result = order.with_user(self.invoicing_user).web_read({"gift_card_count": {}})
        self.assertEqual(result[0]["gift_card_count"], 0)

    def test_user_without_loyalty_access_reads_order_without_error(self):
        # An accounting reader can read sale.order but has no loyalty access
        # at all: the order must still open, with no gift card count.
        accounting_reader = new_test_user(
            self.env,
            login="test_accounting_readonly_user",
            groups="base.group_user,account.group_account_readonly",
            name="Accounting Read-only User",
        )
        order = self._order_with_gift_cards(quantity=2)
        order.action_confirm()
        self.env.invalidate_all()
        result = order.with_user(accounting_reader).web_read({
            "gift_card_count": {},
            "extra_total_fields": {},
        })
        self.assertEqual(result[0]["gift_card_count"], 0)
        self.assertTrue([
            group for group in result[0]["extra_total_fields"] if group["name"] == "loyalty"
        ])

    def test_loyalty_data_readable_by_invoicing_user_on_confirmed_order(self):
        order = self._create_so(
            order_line=[
                Command.create({
                    "product_id": self.product_A.id,
                    "name": "Ordinary Product A",
                    "product_uom_qty": 1.0,
                })
            ]
        )
        order._update_programs_and_rewards()
        self._auto_rewards(order, self.immediate_promotion_program)
        order.action_confirm()

        # action_confirm() above ran as the admin test user and already
        # populated the cache for order.coupon_point_ids.coupon_id, which
        # would let the invoicing user's read below reuse that cached value
        # instead of genuinely exercising its own access rights. Start with
        # a clean cache so the read is forced to go back to the database.
        self.env.invalidate_all()
        result = order.with_user(self.invoicing_user).web_read({"extra_total_fields": {}})

        loyalty_groups = [
            group for group in result[0]["extra_total_fields"] if group["name"] == "loyalty"
        ]
        self.assertTrue(loyalty_groups)
        self.assertIn("label", loyalty_groups[0]["lines"][0])
        self.assertIn("value", loyalty_groups[0]["lines"][0])
