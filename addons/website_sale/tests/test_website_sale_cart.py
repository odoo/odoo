from datetime import datetime
from functools import partial
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.controllers.combo_configurator import (
    WebsiteSaleComboConfiguratorController,
)
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.payment import PaymentPortal
from odoo.addons.website_sale.models.product_template import ProductTemplate
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleCart(ProductVariantsCommon, WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_portal = cls._create_new_portal_user()
        cls.WebsiteSaleController = WebsiteSale()
        cls.WebsiteSaleCartController = Cart()
        cls.public_user = cls.env.ref("base.public_user")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "sale_ok": True,
                "website_published": True,
                "lst_price": 1000.0,
                "standard_price": 800.0,
            }
        )

    def test_add_cart_deleted_product(self):
        product_template_id = self.product.product_tmpl_id
        product_id = self.product.id
        self.product.unlink()
        website = self.website.with_user(self.public_user)

        with self.assertRaises(UserError), MockRequest(website.env, website=website):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=product_template_id,
                product_id=product_id,
                quantity=1,
            )

    def test_add_cart_unpublished_product(self):
        self.product.website_published = False
        website = self.website.with_user(self.public_user)

        with self.assertRaises(UserError), MockRequest(website.env, website=website):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )

        self.product.sale_ok = False
        self.product.website_published = True

        with self.assertRaises(UserError), MockRequest(website.env, website=website):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )

    def test_add_cart_archived_product(self):
        self.product.active = False
        website = self.website.with_user(self.public_user)

        with self.assertRaises(UserError), MockRequest(website.env, website=website):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )

    def test_zero_price_product_rule(self):
        website_prevent_zero_price = self.env["website"].create(
            {
                "name": "Prevent zero price sale",
                "prevent_zero_price_sale": True,
            }
        )
        product_consu = self.env["product.product"].create(
            {
                "name": "Cannot be zero price",
                "type": "consu",
                "list_price": 0,
                "website_published": True,
            }
        )
        product_service = self.env["product.product"].create(
            {
                "name": "Can be zero price",
                "type": "service",
                "list_price": 0,
                "website_published": True,
            }
        )

        with (
            self.assertRaises(
                UserError,
                msg="'consu' product type is not allowed to have a 0 price sale",
            ),
            MockRequest(self.env, website=website_prevent_zero_price),
        ):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=product_consu.product_tmpl_id,
                product_id=product_consu.id,
                quantity=1,
            )

        with (
            patch.object(
                ProductTemplate,
                "_get_product_types_allow_zero_price",
                lambda pt: ["no"],
            ),
            MockRequest(self.env, website=website_prevent_zero_price),
        ):
            with MockRequest(self.env, website=website_prevent_zero_price):
                self.WebsiteSaleCartController.add_to_cart(
                    product_template_id=product_service.product_tmpl_id,
                    product_id=product_service.id,
                    quantity=1,
                )

    def test_update_cart_before_payment(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website) as request:
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )
            sale_order = request.cart
            sale_order.access_token = "test_token"
            old_amount = sale_order.amount_total
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )
            with self.assertRaises(UserError):
                PaymentPortal().shop_payment_transaction(
                    sale_order.id, sale_order.access_token, amount=old_amount
                )

    def test_check_order_delivery_before_payment(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website):
            sale_order = self.env["sale.order"].create(
                {
                    "partner_id": self.public_user.id,
                    "line_ids": [Command.create({"product_id": self.product.id})],
                    "access_token": "test_token",
                }
            )
            with self.assertRaises(ValidationError):
                PaymentPortal().shop_payment_transaction(
                    sale_order.id, sale_order.access_token
                )

    def test_update_cart_zero_qty(self):
        portal_user = self.user_portal
        website = self.website.with_user(portal_user)

        SaleOrderLine = self.env["sale.order.line"]

        with MockRequest(website.env, website=website) as request:
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )
            sale_order = request.cart
            self.assertEqual(sale_order.amount_untaxed, 1000.0)

            self.WebsiteSaleCartController.update_cart(
                line_id=sale_order.line_ids.id,
                quantity=0,
            )
            self.assertEqual(sale_order.amount_total, 0.0)
            self.assertEqual(sale_order.line_ids, SaleOrderLine)

            self.WebsiteSaleCartController.update_cart(
                line_id=sale_order.line_ids.id,
                quantity=0,
            )
            self.assertEqual(sale_order.cart_quantity, 0.0)
            self.assertEqual(sale_order.line_ids, SaleOrderLine)

    def test_unpublished_accessory_product_visibility(self):
        accessory_product = self.env["product.product"].create(
            {
                "name": "Access Product",
                "is_published": False,
            }
        )

        self.product.accessory_product_ids = [Command.link(accessory_product.id)]
        self.empty_cart._cart_add(product_id=self.product.id)
        # the cart controllers read the visitor's cart as the system, under the
        # visitor's own user, which is what decides the published filter
        cart_sudo = self.empty_cart.with_user(self.public_user).sudo()
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website):
            self.assertEqual(len(cart_sudo._cart_accessories()), 0)
            accessory_product.is_published = True
            self.assertEqual(cart_sudo._cart_accessories(), [accessory_product])

    def test_cart_new_fpos_from_geoip(self):
        fpos_be = self.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position BE",
                "country_id": self.country_be.id,
                "company_id": self.company.id,
                "auto_apply": True,
            }
        )

        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, country_code="BE") as request:
            self.assertEqual(request.fiscal_position, fpos_be)
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )
            self.assertEqual(
                request.cart.fiscal_position_id,
                fpos_be,
                "Fiscal position should be determined from GEOIP country for public users.",
            )

    def test_cart_update_with_fpos(self):
        self._enable_pricelists()
        pricelist = self.pricelist
        fpos = self.env["account.fiscal.position"].create(
            {
                "name": "test",
            }
        )
        tax10, tax6 = self.env["account.tax"].create(
            [
                {
                    "name": "Test tax 10",
                    "amount": 10,
                    "price_include_override": "tax_included",
                    "amount_type": "percent",
                },
                {
                    "name": "Test tax 6",
                    "fiscal_position_ids": fpos,
                    "amount": 6,
                    "price_include_override": "tax_included",
                    "amount_type": "percent",
                },
            ]
        )
        tax6.original_tax_ids = tax10

        test_product = self.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 110,
                "taxes_id": [Command.set([tax10.id])],
            }
        )

        pricelist.write(
            {
                "item_ids": [
                    Command.create(
                        {
                            "base": "list_price",
                            "compute_price": "percentage",
                            "percent_price": 50,
                        }
                    ),
                ],
            }
        )

        so = self.env["sale.order"].create(
            {
                "partner_id": self.env.user.partner_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": test_product.id,
                        }
                    )
                ],
            }
        )
        sol = so.line_ids
        self.assertEqual(
            round(sol.price_total), 55.0, "110$ with 50% discount 10% included tax"
        )
        self.assertEqual(
            round(sol.price_tax), 5.0, "110$ with 50% discount 10% included tax"
        )

        so.fiscal_position_id = fpos
        so._recompute_taxes()
        so._cart_update_line_quantity(line_id=sol.id, quantity=2)
        self.assertEqual(
            round(sol.price_total),
            106,
            "2 units @ 100$ with 50% discount + 6% tax (mapped from fp 10% -> 6%)",
        )

    def test_cart_update_with_fpos_no_variant_product(self):
        fpos = self.env["account.fiscal.position"].create(
            {
                "name": "test",
            }
        )
        tax10, tax0 = self.env["account.tax"].create(
            [
                {
                    "name": "Test tax 10",
                    "amount": 10,
                    "price_include_override": "tax_included",
                    "amount_type": "percent",
                },
                {
                    "name": "Test tax 0",
                    "fiscal_position_ids": fpos,
                    "amount": 0,
                    "price_include_override": "tax_included",
                    "amount_type": "percent",
                },
            ]
        )
        tax0.original_tax_ids = tax10

        product_attribute = self.env["product.attribute"].create(
            {
                "name": "test_attr",
                "display_type": "radio",
                "create_variant": "no_variant",
                "value_ids": [
                    Command.create(
                        {
                            "name": "pa_value",
                            "sequence": 1,
                        }
                    ),
                ],
            }
        )

        product_template = self.env["product.template"].create(
            {
                "name": "prod_no_variant",
                "list_price": 110,
                "taxes_id": [Command.set([tax10.id])],
                "is_published": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": product_attribute.id,
                            "value_ids": [Command.set(product_attribute.value_ids.ids)],
                        }
                    ),
                ],
            }
        )
        product = product_template.product_variant_id

        so = self.env["sale.order"].create(
            {
                "partner_id": self.env.user.partner_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                        }
                    )
                ],
            }
        )
        sol = so.line_ids
        self.assertEqual(round(sol.price_total), 110.0, "110$ with 10% included tax")

        so.fiscal_position_id = fpos
        so._recompute_taxes()
        so._cart_update_line_quantity(line_id=sol.id, quantity=2)
        self.assertEqual(
            round(sol.price_total),
            200,
            "200$ with public price+ 0% tax (mapped from fp 10% -> 0%)",
        )

    def test_cart_lines_aggregation(self):
        product_no_variants = self.env["product.template"].create(
            {
                "name": "No variants product (TEST)",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": self.no_variant_attribute.id,
                            "value_ids": [
                                Command.set(self.no_variant_attribute.value_ids.ids)
                            ],
                        }
                    )
                ],
            }
        )
        no_variant_ptavs = (
            product_no_variants.attribute_line_ids.product_template_value_ids
        )
        no_variant_ptav = no_variant_ptavs[0]
        add_one = partial(
            self.empty_cart._cart_add,
            product_id=product_no_variants.product_variant_id.id,
            quantity=1,
        )
        self.assertEqual(len(self.empty_cart.line_ids), 0)

        add_one(no_variant_attribute_value_ids=no_variant_ptav.ids)
        self.assertEqual(len(self.empty_cart.line_ids), 1)

        add_one(no_variant_attribute_value_ids=no_variant_ptav.ids)
        self.assertEqual(len(self.empty_cart.line_ids), 1)
        self.assertEqual(self.empty_cart.line_ids.product_qty, 2)

        product_no_variants.attribute_line_ids.value_ids = (
            self.no_variant_attribute.value_ids[0]
        )
        add_one(no_variant_attribute_value_ids=[])
        self.assertEqual(len(self.empty_cart.line_ids), 1)
        self.assertEqual(self.empty_cart.line_ids.product_qty, 3)

        self.no_variant_attribute.display_type = "multi"
        add_one(no_variant_attribute_value_ids=[])
        self.assertEqual(len(self.empty_cart.line_ids), 2)
        self.assertEqual(self.empty_cart.line_ids.mapped("product_qty"), [3, 1])

        add_one(no_variant_attribute_value_ids=no_variant_ptav.ids)
        self.assertEqual(len(self.empty_cart.line_ids), 2)
        self.assertEqual(self.empty_cart.line_ids.mapped("product_qty"), [4, 1])

    def test_cart_new_pricelist_from_geoip(self):
        self._enable_pricelists()
        eu_group = self.env.ref("base.europe")
        not_eu_group = self.env["res.country.group"].create(
            {
                "name": "Not EU",
                "country_ids": self.env["res.country"]
                .search(
                    [
                        ("id", "not in", eu_group.country_ids.ids),
                    ]
                )
                .ids,
            }
        )

        _pricelist_eu, pricelist_not_eu = self.env["product.pricelist"].create(
            [
                {
                    "name": "EU",
                    "country_group_ids": eu_group.ids,
                    "website_id": self.website.id,
                    "sequence": 1,
                },
                {
                    "name": "Not EU",
                    "country_group_ids": not_eu_group.ids,
                    "website_id": self.website.id,
                    "sequence": 2,
                },
            ]
        )

        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, country_code="US") as request:
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )
            cart = request.cart
            self.assertEqual(cart.pricelist_id, pricelist_not_eu)
            cart.partner_id = self.partner.create({"name": "New Partner"})
            self.assertEqual(cart.pricelist_id, pricelist_not_eu)

    def test_remove_archived_product_line(self):
        user = self.public_user
        website = self.website.with_user(user)
        product = self.env["product.product"].create(
            {
                "name": "Product",
                "sale_ok": True,
                "website_published": True,
            }
        )
        with MockRequest(self.env(user=user), website=website) as request:
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=product.product_tmpl_id,
                product_id=product.id,
                quantity=1,
            )
            order = request.cart

            self.assertRecordValues(
                order.line_ids,
                [
                    {
                        "product_id": product.id,
                    }
                ],
            )
            self.assertTrue(product.active)

            product.active = False
            self.WebsiteSaleCartController.cart()

            self.assertFalse(order.line_ids)

    def test_keep_note_line(self):
        user = self.public_user
        website = self.website.with_user(user)
        with MockRequest(self.env(user=user), website=website) as request:
            order = request.website._create_cart()
            order.line_ids = [
                Command.create(
                    {
                        "name": "Note",
                        "display_type": "line_note",
                    }
                )
            ]

            self.assertRecordValues(
                order.line_ids,
                [
                    {
                        "display_type": "line_note",
                    }
                ],
            )

            self.WebsiteSaleCartController.cart()

            self.assertRecordValues(
                order.line_ids,
                [
                    {
                        "display_type": "line_note",
                    }
                ],
            )

    def test_checkout_no_delivery_method_available(self):
        portal_user = self.user_portal
        website = self.website.with_user(portal_user)
        portal_user.write(self.dummy_partner_address_values)
        self.carrier.country_ids = [Command.set((2,))]
        self.product.type = "consu"
        with (
            MockRequest(website.env, website=website) as request,
            patch(
                "odoo.addons.website_sale.models.sale_order.SaleOrder._get_preferred_delivery_method",
                return_value=self.env["delivery.carrier"],
            ),
        ):
            order = request.website._create_cart()
            order.line_ids = [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "product_qty": 1.0,
                    }
                )
            ]
            self.WebsiteSaleController.shop_checkout()

    def test_add_to_cart_company_branch(self):
        branch_a = self.env["res.company"].create(
            {
                "name": "Branch A",
                "parent_id": self.env.company.id,
            }
        )
        website = self.env["website"].create(
            {
                "name": "Branch A Website",
                "company_id": branch_a.id,
            }
        )
        self.product.company_id = branch_a
        with MockRequest(
            self.product.with_user(website.user_id).env,
            website=website.with_user(website.user_id),
        ):
            branch_a.invalidate_recordset()
            data = WebsiteSaleComboConfiguratorController().website_sale_combo_configurator_get_data(
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                product_tmpl_id=self.product.product_tmpl_id.id,
                quantity=1,
            )
            self.assertEqual(data["quantity"], 1)

    def test_get_cart_after_company_change(self):
        internal_user = self.env.ref("base.user_admin")
        website = self.website.with_user(internal_user)
        with MockRequest(website.env, website=website):
            self.WebsiteSaleCartController.add_to_cart(
                product_template_id=self.product.product_tmpl_id,
                product_id=self.product.id,
                quantity=1,
            )

        other_company = self.env["res.company"].create({"name": "Other Company"})
        internal_user.company_ids = [Command.link(other_company.id)]
        internal_user.company_id = other_company
        with MockRequest(website.env, website=website) as request:
            self.assertFalse(request.cart)
