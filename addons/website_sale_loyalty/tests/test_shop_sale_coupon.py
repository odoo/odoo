from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon
from odoo.addons.website_sale_loyalty.controllers.cart import Cart
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale


@tagged("post_install", "-at_install")
class WebsiteSaleLoyaltyTestUi(TestSaleCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref("base.user_admin").write(
            {
                "company_id": cls.env.company.id,
                "company_ids": [(4, cls.env.company.id)],
                "name": "Mitchell Admin",
                "email": "mitchell.admin@example.com",
                "street": "215 Vine St",
                "phone_ids": [
                    Command.create({"number": "+1 555-555-5555", "type": "landline"})
                ],
                "city": "Scranton",
                "zip": "18503",
                "country_id": cls.env.ref("base.us").id,
                "state_id": cls.env.ref("base.state_us_39").id,
            }
        )
        cls.env.ref("base.user_admin").sudo().partner_id.company_id = cls.env.company
        cls.env.ref("website.default_website").company_id = cls.env.company
        cls.public_category = cls.env["product.public.category"].create(
            {"name": "Public Category"}
        )

    def test_01_admin_shop_sale_loyalty_tour(self):
        if self.env["ir.module.module"]._get("payment_custom").state != "installed":
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref("payment.payment_provider_transfer")
        transfer_provider.sudo().write(
            {
                "state": "enabled",
                "is_published": True,
                "company_id": self.env.company.id,
            }
        )
        transfer_provider._transfer_update_missing_pending_msg()

        large_cabinet = self.env["product.product"].create(
            {
                "name": "Small Cabinet",
                "list_price": 320.0,
                "type": "consu",
                "is_published": True,
                "sale_ok": True,
                "public_categ_ids": [(4, self.public_category.id)],
                "taxes_id": False,
            }
        )

        free_large_cabinet = self.env["product.product"].create(
            {
                "name": "Free Product - Small Cabinet",
                "type": "service",
                "supplier_taxes_id": False,
                "sale_ok": False,
                "purchase_ok": False,
                "invoice_policy": "ordered",
                "default_code": "FREELARGECABINET",
                "taxes_id": False,
            }
        )

        ten_percent = self.env["product.product"].create(
            {
                "name": "10.0% discount on total amount",
                "type": "service",
                "supplier_taxes_id": False,
                "sale_ok": False,
                "purchase_ok": False,
                "invoice_policy": "ordered",
                "default_code": "10PERCENTDISC",
                "taxes_id": False,
            }
        )

        self.env["loyalty.program"].search([]).write({"active": False})

        self.env["loyalty.program"].create(
            {
                "name": "Buy 4 Small Cabinets, get one for free",
                "trigger": "auto",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "minimum_qty": 4,
                            "product_ids": large_cabinet,
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "product",
                            "reward_product_id": large_cabinet.id,
                            "discount_line_product_id": free_large_cabinet.id,
                        },
                    )
                ],
            }
        )

        self.env["loyalty.program"].create(
            {
                "name": "Code for 10% on orders",
                "trigger": "with_code",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "mode": "with_code",
                            "code": "testcode",
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 10,
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                            "discount_line_product_id": ten_percent.id,
                        },
                    )
                ],
            }
        )

        vip_program = self.env["loyalty.program"].create(
            {
                "name": "VIP",
                "trigger": "auto",
                "program_type": "loyalty",
                "portal_visible": True,
                "applies_on": "both",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "mode": "auto",
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 21,
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                            "required_points": 50,
                        },
                    )
                ],
            }
        )

        self.env["loyalty.card"].create(
            {
                "partner_id": self.env.ref("base.partner_admin").id,
                "program_id": vip_program.id,
                "point_name": "Points",
                "points": 371.03,
            }
        )

        self.env.ref("website_sale.reduction_code").write({"active": True})
        self.start_tour("/", "shop_sale_loyalty", login="admin")

    def test_02_admin_shop_gift_card_tour(self):
        gift_card = self.env["product.product"].create(
            {
                "name": "TEST - Gift Card",
                "list_price": 50,
                "type": "service",
                "is_published": True,
                "sale_ok": True,
                "public_categ_ids": [(4, self.public_category.id)],
                "taxes_id": False,
            }
        )
        self.env["product.product"].create(
            {
                "name": "TEST - Small Drawer",
                "list_price": 50,
                "type": "consu",
                "is_published": True,
                "sale_ok": True,
                "public_categ_ids": [(4, self.public_category.id)],
                "taxes_id": False,
            }
        )
        self.env["loyalty.program"].search([]).write({"active": False})

        gift_card_program = self.env["loyalty.program"].create(
            {
                "name": "Gift Cards",
                "program_type": "gift_card",
                "applies_on": "future",
                "trigger": "auto",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_point_amount": 1,
                            "reward_point_mode": "money",
                            "reward_point_split": True,
                            "product_ids": gift_card,
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount_mode": "per_point",
                            "discount": 1,
                            "discount_applicability": "order",
                            "required_points": 1,
                            "description": "PAY WITH GIFT CARD",
                        },
                    )
                ],
            }
        )
        self.env["loyalty.program"].create(
            {
                "name": "10% Discount",
                "applies_on": "current",
                "trigger": "with_code",
                "program_type": "promotion",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "mode": "with_code",
                            "code": "10PERCENT",
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 10,
                            "discount_mode": "percent",
                            "discount_applicability": "order",
                        },
                    )
                ],
            }
        )
        self.env["loyalty.card"].create(
            {
                "program_id": gift_card_program.id,
                "points": 50,
                "code": "GIFT_CARD",
            }
        )

        self.env.ref("website_sale.reduction_code").write({"active": True})
        self.start_tour("/", "shop_sale_gift_card", login="admin")

        self.assertEqual(
            len(gift_card_program.coupon_ids),
            2,
            "There should be two coupons, one with points, one without",
        )
        self.assertEqual(
            len(gift_card_program.coupon_ids.filtered("points")),
            1,
            "There should be two coupons, one with points, one without",
        )

    def test_03_admin_shop_ewallet_tour(self):
        self.env["product.product"].create(
            {
                "name": "TEST - Gift Card",
                "list_price": 50,
                "type": "service",
                "is_published": True,
                "sale_ok": True,
                "public_categ_ids": [(4, self.public_category.id)],
                "taxes_id": False,
            }
        )
        self.env["loyalty.program"].search([]).write({"active": False})
        ewallet_programs = self.env["loyalty.program"].create(
            [
                {
                    "name": f"ewallet - test - {ecommerce_ok=}",
                    "applies_on": "future",
                    "trigger": "auto",
                    "program_type": "ewallet",
                    "ecommerce_ok": ecommerce_ok,
                    "reward_ids": [
                        Command.create(
                            {
                                "reward_type": "discount",
                                "discount_mode": "per_point",
                                "discount": 1,
                            }
                        )
                    ],
                }
                for ecommerce_ok in (True, False)
            ]
        )
        self.env["loyalty.card"].create(
            [
                {
                    "partner_id": self.env.ref("base.partner_admin").id,
                    "program_id": program_id,
                    "points": 1000,
                }
                for program_id in ewallet_programs.ids
            ]
        )
        self.start_tour("/", "shop_sale_ewallet", login="admin")


@tagged("post_install", "-at_install")
class TestWebsiteSaleCoupon(HttpCase, WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        program = cls.env["loyalty.program"].create(
            {
                "name": "10% TEST Discount",
                "trigger": "with_code",
                "applies_on": "current",
                "rule_ids": [(0, 0, {})],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 10,
                            "discount_mode": "percent",
                        },
                    )
                ],
            }
        )

        cls.env["loyalty.generate.wizard"].with_context(active_id=program.id).create(
            {"coupon_qty": 1, "points_granted": 1}
        ).generate_coupons()
        cls.coupon = program.coupon_ids[0]

    def _apply_promo_code(self, order, code, no_reward_fail=True):
        status = order._try_apply_code(code)
        if "error" in status:
            raise ValidationError(status["error"])
        if not status and no_reward_fail:
            raise ValidationError("No reward to claim with this coupon")
        coupons = self.env["loyalty.card"]
        rewards = self.env["loyalty.reward"]
        for coupon, coupon_rewards in status.items():
            coupons |= coupon
            rewards |= coupon_rewards
        if len(coupons) == 1 and len(rewards) == 1:
            status = order._apply_program_reward(rewards, coupons)
            if "error" in status:
                raise ValidationError(status["error"])

    def test_01_gc_coupon(self):
        order = self.empty_cart
        order.line_ids = [
            Command.create(
                {
                    "product_id": self.env["product.product"]
                    .create(
                        {
                            "name": "Product A",
                            "list_price": 100,
                            "sale_ok": True,
                        }
                    )
                    .id,
                    "product_qty": 2.0,
                }
            )
        ]

        self._apply_promo_code(order, self.coupon.code)

        self.assertEqual(
            len(order.applied_coupon_ids),
            1,
            "The coupon should've been applied on the order",
        )
        self.assertEqual(self.coupon, order.applied_coupon_ids)

        order._gc_abandoned_coupons()

        self.assertEqual(
            len(order.applied_coupon_ids),
            1,
            "The coupon shouldn't have been removed from the order no more than 4 days",
        )

        ICP = self.env["ir.config_parameter"]
        icp_validity = ICP.create(
            {"key": "website_sale_coupon.abandonned_coupon_validity", "value": 5}
        )
        self.env.flush_all()
        query = """UPDATE %s SET write_date = %%s WHERE id = %%s""" % (order._table,)
        self.env.cr.execute(
            query,
            (
                fields.Datetime.to_string(
                    fields.Datetime.now() - timedelta(days=4, hours=2)
                ),
                order.id,
            ),
        )
        order._gc_abandoned_coupons()

        self.assertEqual(
            len(order.applied_coupon_ids),
            1,
            "The coupon shouldn't have been removed from the order the order is 4 days old but icp validity is 5 days",
        )

        icp_validity.unlink()
        order._gc_abandoned_coupons()

        self.assertEqual(
            len(order.applied_coupon_ids),
            0,
            "The coupon should've been removed from the order as more than 4 days",
        )

    def test_02_apply_discount_code_program_multi_rewards(self):
        self.env["loyalty.program"].search([]).write({"active": False})
        chair = self.env["product.product"].create(
            {"name": "Super Chair", "list_price": 1000, "website_published": True}
        )
        self.discount_code_program_multi_rewards = self.env["loyalty.program"].create(
            {
                "name": "Discount code program",
                "program_type": "promo_code",
                "applies_on": "current",
                "trigger": "with_code",
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "code": "12345",
                            "reward_point_amount": 1,
                            "reward_point_mode": "order",
                        },
                    )
                ],
                "reward_ids": [
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 10,
                            "discount_applicability": "specific",
                            "required_points": 1,
                            "discount_product_ids": chair,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "reward_type": "discount",
                            "discount": 50,
                            "discount_applicability": "order",
                            "required_points": 1,
                        },
                    ),
                ],
            }
        )
        self.start_tour("/", "apply_discount_code_program_multi_rewards", login="admin")

    def test_03_remove_coupon(self):
        order = self.empty_cart
        order.line_ids = [
            Command.create(
                {
                    "product_id": self.env["product.product"]
                    .create({"name": "Product A", "list_price": 100, "sale_ok": True})
                    .id,
                }
            )
        ]

        self._apply_promo_code(order, self.coupon.code)

        coupon_line = order.website_order_line.filtered(
            lambda l: l.coupon_id and l.coupon_id.id == self.coupon.id
        )

        website = self.website
        with MockRequest(website.env, website=self.website, sale_order_id=order.id):
            Cart().update_cart(
                line_id=None,
                quantity=0.0,
                product_id=coupon_line.product_id.id,
            )

        msg = "The coupon should've been removed from the order"
        self.assertEqual(len(order.applied_coupon_ids), 0, msg=msg)

    def test_04_apply_coupon_code_twice(self):
        product = self.env["product.product"].create(
            {
                "name": "Product",
                "list_price": 100,
                "sale_ok": True,
                "taxes_id": [],
            }
        )

        order = self.empty_cart
        order.line_ids = [Command.create({"product_id": product.id})]

        WebsiteSaleController = WebsiteSale()

        installed_modules = set(
            self.env["ir.module.module"]
            .search(
                [
                    ("state", "=", "installed"),
                ]
            )
            .mapped("name")
        )
        for _ in http._generate_routing_rules(installed_modules, nodb_only=False):
            pass

        with MockRequest(
            self.env, website=self.website, sale_order_id=order.id
        ) as request:
            self.assertEqual(
                order.amount_total, 100.0, "The base cart value is incorrect."
            )

            WebsiteSaleController.pricelist(promo=self.coupon.code)

            self.assertEqual(order.amount_total, 90.0, "The coupon is not applied.")

            WebsiteSaleController.pricelist(promo=self.coupon.code)
            Cart().cart()
            error_msg = request.session.get("error_promo_code")

            self.assertEqual(
                bool(error_msg),
                True,
                "Apply a coupon twice should display an error message",
            )
            self.assertEqual(
                order.amount_total, 90.0, "Apply a coupon twice shouldn't delete it"
            )

    def test_03_remove_coupon_with_different_taxes_on_products(self):
        tax_a = self.env["account.tax"].create(
            {
                "name": "Tax A",
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 15,
            }
        )
        tax_b = tax_a.copy({"name": "Tax B"})

        products_data = [
            ("Product A", []),
            ("Product B", [tax_a.id]),
            ("Product C", [tax_b.id]),
            ("Product D", [tax_a.id, tax_b.id]),
        ]

        products = self.env["product.product"].create(
            [
                {
                    "name": name,
                    "list_price": 100,
                    "sale_ok": True,
                    "taxes_id": [Command.set(taxes_id)],
                }
                for name, taxes_id in products_data
            ]
        )

        order = self.empty_cart
        order.line_ids = [
            Command.create({"product_id": product.id}) for product in products
        ]

        msg = "There should only be 4 lines for the 4 products."
        self.assertEqual(len(order.line_ids), 4, msg=msg)

        self._apply_promo_code(order, self.coupon.code)

        msg = (
            "4 additional lines should have been added to the sale orders"
            "after application of the coupon for each separate tax situation."
        )
        self.assertEqual(len(order.line_ids), 8, msg=msg)

        coupon_line = order.website_order_line.filtered(
            lambda line: line.coupon_id and line.coupon_id.id == self.coupon.id
        )
        website = self.website
        with MockRequest(website.env, website=self.website, sale_order_id=order.id):
            Cart().update_cart(
                line_id=None,
                quantity=0.0,
                product_id=coupon_line.product_id.id,
            )

        msg = "All coupon lines should have been removed from the order."
        self.assertEqual(len(order.applied_coupon_ids), 0, msg=msg)
        self.assertEqual(len(order.line_ids), 4, msg=msg)

    def test_confirm_points_as_public_user(self):
        test_product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 100,
                "sale_ok": True,
            }
        )
        test_partner = self.env["res.partner"].create({"name": "Test Partner"})

        loyalty_program = self.env["loyalty.program"].create(
            {
                "name": "Loyalty Program",
                "program_type": "loyalty",
                "trigger": "auto",
                "applies_on": "both",
                "rule_ids": [
                    Command.create(
                        {
                            "reward_point_mode": "unit",
                            "reward_point_amount": 1,
                            "product_ids": [test_product.id],
                        }
                    )
                ],
                "reward_ids": [
                    Command.create(
                        {
                            "reward_type": "discount",
                            "discount": 1.5,
                            "discount_mode": "per_point",
                            "discount_applicability": "order",
                            "required_points": 3,
                        }
                    )
                ],
            }
        )

        order = self.env["sale.order"].create(
            {
                "partner_id": test_partner.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": test_product.id,
                            "product_qty": 1,
                        }
                    )
                ],
            }
        )

        loyalty_card = self.env["loyalty.card"].create(
            {
                "program_id": loyalty_program.id,
                "partner_id": test_partner.id,
                "points": 0,
            }
        )
        public_user = self.env.ref("base.public_user")
        order.action_send_quotation()
        order.with_context(
            access_token=order.access_token, user=public_user
        ).action_confirm()
        self.assertEqual(loyalty_card.points, 1)
