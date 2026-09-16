import logging

from odoo import Command
from odoo.http import Request, root
from odoo.tests import HttpCase, tagged
from odoo.tests.common import JsonRpcException
from odoo.tools import mute_logger

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestShopAddressInputCoercion(HttpCase, WebsiteSaleCommon):
    @mute_logger("odoo.http")
    def test_shop_address_non_numeric_partner_id(self):
        response = self.url_open("/shop/address?partner_id=abc")
        self.assertNotEqual(response.status_code, 500)

    @mute_logger("odoo.http")
    def test_shop_address_junk_use_delivery_as_billing(self):
        for value in ("xyz", "2", " true", "True%20"):
            with self.subTest(value=value):
                response = self.url_open(
                    f"/shop/address?use_delivery_as_billing={value}"
                )
                self.assertNotEqual(response.status_code, 500)

    @mute_logger("odoo.http")
    def test_shop_checkout_junk_try_skip_step(self):
        response = self.url_open("/shop/checkout?try_skip_step=xyz")
        self.assertNotEqual(response.status_code, 500)

    def test_shop_address_recognised_flag_still_honoured(self):
        for value in ("true", "1", "on"):
            with self.subTest(value=value):
                response = self.url_open(
                    f"/shop/address?use_delivery_as_billing={value}"
                )
                self.assertNotEqual(response.status_code, 500)


@tagged("post_install", "-at_install")
class TestShopListingInputCoercion(HttpCase, WebsiteSaleCommon):
    @mute_logger("odoo.http")
    def test_shop_junk_attribute_values(self):
        for value in ("5", "abc-1", "1-xyz", "1-", "-", "a-b"):
            with self.subTest(value=value):
                response = self.url_open(f"/shop?attribute_values={value}")
                self.assertNotEqual(response.status_code, 500)

    @mute_logger("odoo.http")
    def test_shop_well_formed_attribute_values_still_parse(self):
        parsed = WebsiteSale._get_attribute_value_dict(["1-2,3", "4-5"])
        self.assertEqual(parsed, {1: [2, 3], 4: [5]})

    def test_valid_entries_survive_a_malformed_sibling(self):
        parsed = WebsiteSale._get_attribute_value_dict(["1-2", "garbage", "4-5"])
        self.assertEqual(parsed, {1: [2], 4: [5]})

    @mute_logger("odoo.http")
    def test_recently_viewed_routes_survive_non_numeric_ids(self):
        for route, params in (
            ("/shop/products/recently_viewed_update", {"product_id": "abc"}),
            ("/shop/products/recently_viewed_delete", {"product_id": "abc"}),
            ("/shop/products/recently_viewed_delete", {"product_template_id": "abc"}),
        ):
            with self.subTest(route=route, params=params):
                try:
                    self.call_jsonrpc(route, params=params)
                except JsonRpcException as exc:
                    self.assertNotIn("ValueError", str(exc))


@tagged("post_install", "-at_install")
class TestShopAddressReservedParams(HttpCase, WebsiteSaleCommon):
    def setUp(self):
        super().setUp()
        self.cart.partner_id.write(
            {
                "street": "1 Test Street",
                "city": "Testville",
                "zip": "1000",
                "country_id": self.country_be.id,
                "email": "reserved.params@example.com",
                "phone_ids": [
                    Command.create({"number": "+32 2 000 00 00", "type": "landline"})
                ],
            }
        )
        self.cart.write(
            {
                "partner_invoice_id": self.cart.partner_id.id,
                "partner_shipping_id": self.cart.partner_id.id,
            }
        )
        session = self.authenticate(None, None)
        session["sale_order_id"] = self.cart.id
        root.session_store.save(session)

    def _reserved_keys(self):
        return sorted(WebsiteSale()._get_reserved_address_form_keys() | {"order_sudo"})

    def _assert_reaches_the_route(self, url):
        response = self.url_open(url, allow_redirects=False)
        self.assertEqual(
            response.status_code,
            200,
            f"{url} must render the page, else this test proves nothing "
            f"(got {response.status_code})",
        )

    @mute_logger("odoo.http")
    def test_shop_address_get_ignores_reserved_query_params(self):
        self._assert_reaches_the_route("/shop/address")
        for key in self._reserved_keys():
            with self.subTest(key=key):
                response = self.url_open(
                    f"/shop/address?{key}=x", allow_redirects=False
                )
                self.assertEqual(
                    response.status_code,
                    200,
                    f"query param {key!r} must not rebind an internal argument",
                )

    @mute_logger("odoo.http")
    def test_shop_checkout_ignores_reserved_query_params(self):
        self._assert_reaches_the_route("/shop/checkout")
        for key in self._reserved_keys():
            with self.subTest(key=key):
                response = self.url_open(
                    f"/shop/checkout?{key}=x", allow_redirects=False
                )
                self.assertEqual(
                    response.status_code,
                    200,
                    f"query param {key!r} must not rebind an internal argument",
                )

    def test_order_sudo_is_in_the_reserved_set(self):
        self.assertIn("order_sudo", WebsiteSale()._get_reserved_address_form_keys())


@tagged("post_install", "-at_install")
class TestShopCompanyNameBoundary(HttpCase, WebsiteSaleCommon):
    def test_public_token_chatter_ownership_and_invalid_token(self):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "shared.txt",
                "raw": b"Public token attachment",
                "res_model": "sale.order",
                "res_id": self.cart.id,
            }
        )
        own_message, internal_message = self.env["mail.message"].create(
            [
                {
                    "model": "sale.order",
                    "res_id": self.cart.id,
                    "body": "Token chatter test",
                    "message_type": "comment",
                    "subtype_id": self.env.ref("mail.mt_comment").id,
                    "author_id": author.id,
                    "attachment_ids": [Command.link(attachment.id)],
                }
                for author in (self.customer, self.env.user.partner_id)
            ]
        )
        params = {
            "thread_model": "sale.order",
            "thread_id": self.cart.id,
            "token": self.cart._portal_get_or_create_token(),
        }

        result = self.call_jsonrpc("/mail/chatter_fetch", params)

        attachments = {
            message["id"]: message["attachment_ids"][0]
            for message in result["data"]["mail.message"]
            if message["id"] in (own_message | internal_message).ids
        }
        _logger.debug(
            "Public token ownership flags: %s",
            {key: "ownership_token" in value for key, value in attachments.items()},
        )
        self.assertIn("ownership_token", attachments[own_message.id])
        self.assertNotIn("ownership_token", attachments[internal_message.id])
        response = self.url_open(
            "/mail/chatter_fetch", json={"params": {**params, "token": "invalid"}}
        ).json()
        self.assertEqual(response["error"]["code"], 404)

    def setUp(self):
        super().setUp()
        self.customer_company = self.env["res.partner"].create(
            {"name": "Checkout shared company", "is_company": True}
        )
        self.customer = self.env["res.partner"].create(
            {"name": "Checkout customer", "parent_id": self.customer_company.id}
        )
        self.shipping = self.env["res.partner"].create(
            {
                "name": "Checkout shipping",
                "parent_id": self.customer_company.id,
                "type": "delivery",
            }
        )
        self.cart.write(
            {
                "partner_id": self.customer.id,
                "partner_invoice_id": self.customer.id,
                "partner_shipping_id": self.shipping.id,
            }
        )
        session = self.authenticate(None, None)
        session["sale_order_id"] = self.cart.id
        root.session_store.save(session)

    def _submit_company_name(self, partner_id="", address_type="billing"):
        response = self.url_open(
            "/shop/address/submit",
            data={
                "partner_id": partner_id,
                "address_type": address_type,
                "name": "Submitted checkout customer",
                "email": "checkout.company@example.com",
                "phone": "+32 2 000 00 00",
                "street": "1 Test Street",
                "city": "Brussels",
                "zip": "1000",
                "country_id": self.country_be.id,
                "company_name": "Submitted checkout company",
                "csrf_token": Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        _logger.debug(
            "Checkout company submission target=%s type=%s result=%s",
            partner_id,
            address_type,
            result,
        )
        self.assertIn("redirectUrl", result)
        self.cart.invalidate_recordset()
        self.customer_company.invalidate_recordset()

    def test_anonymous_first_address_can_create_company(self):
        self.cart.write(
            {
                "partner_id": self.public_partner.id,
                "partner_invoice_id": self.public_partner.id,
                "partner_shipping_id": self.public_partner.id,
            }
        )
        public_name = self.public_partner.name

        self._submit_company_name()

        self.assertNotEqual(self.cart.partner_id, self.public_partner)
        self.assertEqual(self.cart.partner_id.name, "Submitted checkout customer")
        self.assertEqual(
            self.cart.partner_id.commercial_partner_id.name,
            "Submitted checkout company",
        )
        self.public_partner.invalidate_recordset()
        self.assertEqual(self.public_partner.name, public_name)

    def test_existing_shipping_cannot_rename_company(self):
        self._submit_company_name(self.shipping.id, "delivery")

        self.assertEqual(self.customer_company.name, "Checkout shared company")
        self.shipping.invalidate_recordset()
        self.assertEqual(self.shipping.name, "Submitted checkout customer")

    def test_new_shipping_cannot_rename_company(self):
        self._submit_company_name(address_type="delivery")

        self.assertEqual(self.customer_company.name, "Checkout shared company")
        self.assertNotEqual(self.cart.partner_shipping_id, self.shipping)
        self.assertEqual(
            self.cart.partner_shipping_id.name, "Submitted checkout customer"
        )

    def test_main_address_can_rename_company(self):
        self._submit_company_name(self.customer.id)

        self.assertEqual(self.customer_company.name, "Submitted checkout company")
