# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class TestPromotionTracking(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website.google_analytics_key = "G-XXXXXXXXXXX"
        cls.gift = cls.env["product.product"].create({
            "name": "Promotional gift", "default_code": "GA-GIFT", "list_price": 25,
        })
        cls.program = cls.env["loyalty.program"].create({
            "name": "Tracking promotion", "program_type": "promotion",
            "reward_ids": [Command.create({
                "reward_type": "discount", "discount": 10,
                "discount_applicability": "specific",
                "discount_product_ids": [Command.set(cls.product.ids)],
            })],
        })
        cls.reward = cls.program.reward_ids

    def test_specific_discount_excludes_unrelated_cart_products(self):
        info = self.cart.sudo()._get_promotion_tracking_info(self.reward)
        self.assertEqual(info["items"], [{
            **self.cart._get_order_line_tracking_data(self.cart.order_line.filtered(
                lambda line: line.product_id == self.product
            )), "quantity": 5,
        }])

    def test_product_reward_tracks_gift_outside_cart(self):
        self.reward.sudo().write({"reward_type": "product", "reward_product_id": self.gift.id})
        info = self.cart.sudo()._get_promotion_tracking_info(self.reward)
        self.assertEqual(info["items"], [{
            "item_id": "GA-GIFT", "item_name": "Promotional gift", "quantity": 1,
        }])
        self.assertEqual(info["product_items"][str(self.gift.id)], info["items"][0])

    def test_order_discount_tracks_order_products(self):
        self.reward.sudo().discount_applicability = "order"
        info = self.cart.sudo()._get_promotion_tracking_info(self.reward)
        self.assertEqual(info["items"], self.cart._get_order_tracking_items())

    def test_cheapest_discount_tracks_one_unit_of_cheapest_product(self):
        self.reward.sudo().discount_applicability = "cheapest"
        line = self.cart.sudo()._cheapest_line(self.reward)
        info = self.cart.sudo()._get_promotion_tracking_info(self.reward)
        self.assertEqual(info["items"], [{
            **self.cart._get_order_line_tracking_data(line), "quantity": 1,
        }])

    def test_no_analytics_returns_no_promotion_payload(self):
        self.website.sudo().google_analytics_key = False
        self.assertEqual(self.cart.sudo()._get_promotion_tracking_info(self.reward), {})
