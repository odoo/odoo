from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.cart import Cart
from odoo.addons.website_sale_loyalty.controllers.delivery import (
    WebsiteSaleLoyaltyDelivery,
)


@tagged("post_install", "-at_install")
class TestWebsiteSaleDelivery(HttpCase, WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Controller = WebsiteSaleLoyaltyDelivery()

        cls.env = cls.env["base"].with_context(**DISABLED_MAIL_CONTEXT).env
        cls.env["product.pricelist"].with_context(active_test=False).search([]).unlink()
        cls.env["loyalty.program"].search([]).active = False
        cls.env.companies.account_config_id.account_sale_tax_id = False

        cls.user_admin = cls.env.ref("base.user_admin")
        cls.partner_admin = cls.user_admin.partner_id
        cls.partner_admin.write(cls.dummy_partner_address_values)

        cls.website2 = cls.env["website"].create({"name": "website 2"})

        cls.product_plumbus = cls.env["product.product"].create(
            {
                "name": "Plumbus",
                "list_price": 100.0,
                "type": "consu",
                "website_published": True,
            }
        )

        cls.product_gift_card = cls.env["product.product"].create(
            {
                "name": "TEST - Gift Card",
                "list_price": 50,
                "type": "service",
                "is_published": True,
            }
        )

        gift_card_program = cls.env["loyalty.program"].create(
            {
                "name": "Gift Cards",
                "program_type": "gift_card",
                "applies_on": "future",
                "trigger": "auto",
                "rule_ids": [
                    Command.create(
                        {
                            "reward_point_amount": 1,
                            "reward_point_mode": "money",
                            "reward_point_split": True,
                            "product_ids": cls.product_gift_card.ids,
                        }
                    )
                ],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "discount",
                            "discount_mode": "per_point",
                            "discount": 1,
                            "discount_applicability": "order",
                            "required_points": 1,
                            "description": "PAY WITH GIFT CARD",
                        }
                    )
                ],
            }
        )

        cls.gift_card = cls.env["loyalty.card"].create(
            {
                "program_id": gift_card_program.id,
                "points": 50000,
                "code": "123456",
            }
        )

        cls.promo_discount_code = cls.env["loyalty.program"].create(
            {
                "name": "50% discount code",
                "program_type": "promo_code",
                "trigger": "with_code",
                "applies_on": "current",
                "rule_ids": [
                    Command.create(
                        {
                            "code": "test-50pc",
                        }
                    )
                ],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "discount",
                            "discount": 50.0,
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                        }
                    )
                ],
            }
        )

        ewallet_program = cls.env["loyalty.program"].create(
            {
                "name": "eWallet",
                "program_type": "ewallet",
                "applies_on": "future",
                "trigger": "auto",
                "reward_ids": [
                    Command.create(
                        {
                            "description": "Pay with eWallet",
                            "reward_type": "discount",
                            "discount_mode": "per_point",
                            "discount": 1,
                        }
                    )
                ],
            }
        )

        cls.ewallet = cls.env["loyalty.card"].create(
            {
                "program_id": ewallet_program.id,
                "partner_id": cls.partner_admin.id,
                "points": 1000000,
            }
        )

        delivery_product1, delivery_product2 = cls.env["product.product"].create(
            [
                {
                    "name": "Delivery 1",
                    "invoice_policy": "ordered",
                    "type": "service",
                },
                {
                    "name": "Delivery 2",
                    "invoice_policy": "ordered",
                    "type": "service",
                },
            ]
        )

        cls.normal_delivery, cls.normal_delivery2 = cls.env["delivery.carrier"].create(
            [
                {
                    "name": "delivery1",
                    "fixed_price": 5,
                    "delivery_type": "fixed",
                    "website_published": True,
                    "product_id": delivery_product1.id,
                },
                {
                    "name": "delivery2",
                    "fixed_price": 10,
                    "delivery_type": "fixed",
                    "website_published": True,
                    "product_id": delivery_product2.id,
                },
            ]
        )

    def create_program_with_code(self, code, website_id):
        return self.env["loyalty.program"].create(
            {
                "name": "Discount delivery",
                "program_type": "promo_code",
                "website_id": website_id.id,
                "rule_ids": [
                    Command.create(
                        {
                            "code": code,
                            "minimum_amount": 0,
                        }
                    )
                ],
            }
        )

    def test_shop_sale_gift_card_keep_delivery(self):
        self.partner_admin.property_delivery_carrier_id = self.normal_delivery
        self.start_tour("/", "shop_sale_loyalty_delivery", login="admin")

    def test_shipping_discount(self):
        self.env["loyalty.program"].create(
            {
                "name": "Buy 3, get up to $6 discount on shipping!",
                "program_type": "promotion",
                "applies_on": "current",
                "trigger": "auto",
                "rule_ids": [
                    Command.create(
                        {
                            "minimum_qty": 3.0,
                        }
                    )
                ],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "shipping",
                            "discount_max_amount": 6.0,
                        }
                    )
                ],
            }
        )
        self.start_tour("/", "check_shipping_discount", login="admin")

    def test_update_shipping_after_discount(self):
        self.free_delivery.action_archive()
        self.normal_delivery.write({"free_over": True, "amount": 75.0})
        self.start_tour(
            "/shop", "update_shipping_after_discount", login=self.user_admin.login
        )

    def test_express_checkout_shipping_discount(self):
        program = (
            self.env["loyalty.program"]
            .sudo()
            .create(
                {
                    "name": "Free Shipping",
                    "program_type": "promo_code",
                    "rule_ids": [
                        Command.create(
                            {
                                "code": "FREE",
                                "minimum_amount": 0,
                            }
                        )
                    ],
                    "reward_ids": [
                        Command.create(
                            {
                                "reward_type": "shipping",
                                "discount_max_amount": 6.0,
                            }
                        )
                    ],
                }
            )
        )

        self.cart._try_apply_code("FREE")
        self.cart._apply_program_reward(program.reward_ids, program.coupon_ids)

        with MockRequest(self.env, sale_order_id=self.cart.id, website=self.website):
            result = self.Controller.shop_set_delivery_method(self.normal_delivery2.id)
        self.assertEqual(result["delivery_discount_minor_amount"], -600)

    def test_express_checkout_does_not_count_delivery_discount_in_payment_values(self):
        program = (
            self.env["loyalty.program"]
            .sudo()
            .create(
                {
                    "name": "Discount delivery",
                    "program_type": "promo_code",
                    "rule_ids": [
                        Command.create(
                            {
                                "code": "FREE",
                                "minimum_amount": 0,
                            }
                        )
                    ],
                    "reward_ids": [
                        Command.create(
                            {
                                "reward_type": "shipping",
                                "discount_max_amount": 2.0,
                            }
                        )
                    ],
                }
            )
        )
        amount_without_delivery = payment_utils.major_to_minor_currency_units(
            self.cart.amount_total, self.cart.currency_id
        )
        self.cart.set_delivery_line(
            self.normal_delivery, self.normal_delivery.fixed_price
        )
        self.cart._try_apply_code("FREE")
        self.cart._apply_program_reward(program.reward_ids, program.coupon_ids)
        with MockRequest(self.env, sale_order_id=self.cart.id, website=self.website):
            payment_values = Cart()._get_express_shop_payment_values(self.cart)

        self.assertEqual(payment_values["minor_amount"], amount_without_delivery)

    def test_prevent_unarchive_when_conflicting_active_program_exists_on_same_website(
        self,
    ):
        program = self.create_program_with_code("FREE", self.website)
        program.action_archive()
        self.create_program_with_code("FREE", self.website)

        with self.assertRaises(ValidationError):
            program.action_unarchive()

    def test_unarchive_when_conflicting_active_program_exists_on_different_website(
        self,
    ):
        program = self.create_program_with_code("FREE", self.website)
        program.action_archive()

        self.create_program_with_code("FREE", self.website2)
        program.action_unarchive()

    def test_prevent_unarchive_when_batch_contains_duplicate_codes_on_same_website(
        self,
    ):
        program1 = self.create_program_with_code("FREE", self.website)
        program1.action_archive()
        program2 = self.create_program_with_code("FREE", self.website)
        program2.action_archive()

        with self.assertRaises(ValidationError):
            (program1 + program2).action_unarchive()
