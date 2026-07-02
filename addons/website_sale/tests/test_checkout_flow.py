# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import patch, tagged
from odoo.tests.common import HttpCase

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.cart import Cart as CartController
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.controllers.payment import PaymentPortal as PaymentController
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged("post_install", "-at_install")
class TestCheckoutFlow(WebsiteSaleCommon, PaymentCommon, HttpCase):
    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist = cls._enable_pricelists()
        cls.partner.write(cls.dummy_partner_address_values)
        cls.cart.pricelist_id = cls.pricelist
        cls.CheckoutController = CheckoutController()
        cls.CartController = CartController()
        cls.PaymentController = PaymentController()

    def assert_redirected_to(self, response, expected):
        self.assertEqual(response.status_code, 303, "SEE OTHER")
        self.assertURLEqual(response.location, expected)

    def test_checkout_step_validation_redirects_to_the_first_invalid_step(self):
        self.cart.order_line = False  # An order line is required to go to checkout
        self.cart.carrier_id = False

        with self.mock_request(path="/shop/payment", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_payment()

        self.assert_redirected_to(response, "/shop/cart")  # Redirected back to the cart page first

    def test_impossible_to_checkout_without_a_cart(self):
        with self.mock_request(path="/shop/checkout"):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, "/shop")

    def test_impossible_to_checkout_without_cart_in_draft(self):
        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            for state in ("sent", "sale", "cancel"):
                with self.subTest(state=state):
                    self.cart.state = state

                    response = self.CheckoutController.shop_checkout()

                    self.assert_redirected_to(response, "/shop")

    def test_impossible_to_checkout_with_empty_cart(self):
        self.cart.order_line = False

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, "/shop/cart")

    def test_asked_to_login_if_account_on_checkout_mandatory(self):
        self.website.account_on_checkout = "mandatory"

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, "/web/login?redirect=/shop/checkout")

    def test_impossible_to_checkout_if_a_product_is_sold_out(self):
        self.product.write({"is_storable": True, "allow_out_of_stock_order": False, "free_qty": 0})

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assertURLEqual(response.location, "/shop/cart")  # Redirected back to the cart

    def test_impossible_to_checkout_with_public_partner(self):
        self.cart.partner_id = self.public_partner

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, "/shop/address")  # Must create a partner first

    def test_cart_must_have_a_billing_address(self):
        (self.cart.partner_shipping_id, self.cart.partner_invoice_id) = self.env[
            "res.partner"
        ].create([
            dict(
                self.dummy_partner_address_values,
                name="dummy",
                type="delivery",
                parent_id=self.partner.id,
            ),
            # Invalid billing address
            dict(
                self.dummy_partner_address_values,
                name="dummy",
                type="invoice",
                parent_id=self.partner.id,
                email=False,
            ),
        ])

        self.assertFalse(self.cart.partner_invoice_id.email)
        self.assertIn(self.cart.partner_shipping_id, self.cart.partner_id.child_ids)
        self.assertIn(self.cart.partner_invoice_id, self.cart.partner_id.child_ids)

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(
            response,
            f"/shop/address?partner_id={self.cart.partner_invoice_id.id}&address_type=billing",
        )

    def test_cart_must_have_a_delivery_address(self):
        (self.cart.partner_shipping_id, self.cart.partner_invoice_id) = self.env[
            "res.partner"
        ].create([
            # Invalid delivery address
            dict(
                self.dummy_partner_address_values,
                name="dummy",
                type="delivery",
                parent_id=self.partner.id,
                email=False,
            ),
            # Invalid billing address
            dict(
                self.dummy_partner_address_values,
                name="dummy",
                type="invoice",
                parent_id=self.partner.id,
            ),
        ])

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(
            response,
            f"/shop/address?partner_id={self.cart.partner_shipping_id.id}&address_type=delivery",
        )

    def test_impossible_to_confirm_if_no_delivery_method_available(self):
        self.env["delivery.carrier"].search([]).action_archive()
        self.env["delivery.carrier"].create({
            "name": "Local BE",
            "country_ids": self.country_be.ids,
            "product_id": self.free_delivery.product_id.id,
        })
        self.cart.partner_shipping_id.country_id = self.country_us  # No DM can ship to the US
        self.cart.partner_shipping_id.state_id = self.country_us_state_id

        with self.mock_request(path="/shop/payment", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_payment()

        # Customer must change his address of delivery
        self.assert_redirected_to(response, "/shop/checkout")

    def test_impossible_to_confirm_if_no_delivery_method_is_selected(self):
        self.cart.carrier_id = False

        with self.mock_request(path="/shop/payment", sale_order_id=self.cart.id):
            # Assume the user is on the checkout page and clicks on the "Confirm" button
            response = self.CheckoutController.shop_payment()

        self.assert_redirected_to(response, "/shop/checkout")  # Redirected back to the checkout

    def test_alerts_cleared_when_rendering_a_checkout_step(self):
        self.authenticate(None, None)
        self.update_session(**{CART_SESSION_CACHE_KEY: self.cart.id})

        with patch(
            "odoo.addons.website_sale.models.sale_order.SaleOrder._clear_alerts", autospec=True
        ) as clear_alerts_mock:
            self.url_open("/shop/cart")

            clear_alerts_mock.assert_called_once()

    def test_final_payment_step_check_all_checkout_steps(self):
        self.authenticate(None, None)
        self.update_session(**{CART_SESSION_CACHE_KEY: self.cart.id})

        def patch_check(method):
            return patch.object(
                self.env.registry["website.checkout.step"], method, return_value=None
            )

        with (
            patch_check("_check_shop_cart_completion") as check_shop_cart_completion,
            patch_check("_check_shop_address_completion") as check_shop_address_completion,
            patch_check("_check_shop_checkout_completion") as check_shop_checkout_completion,
            patch_check("_check_shop_payment_completion") as check_shop_payment_completion,
        ):
            self.url_open("/shop/payment")

            check_shop_cart_completion.assert_called_once()
            check_shop_address_completion.assert_called_once()
            check_shop_checkout_completion.assert_called_once()
            check_shop_payment_completion.assert_not_called()

            self.make_jsonrpc_request(
                f"/shop/payment/transaction/{self.cart.id}",
                params={
                    "provider_id": self.provider.id,
                    "payment_method_id": self.payment_method.id,
                    "token_id": None,
                    "flow": "direct",
                    "tokenization_requested": False,
                    "landing_route": "/shop/payment/validate",
                    "access_token": self.cart._portal_ensure_token(),
                },
            )

            self.assertEqual(check_shop_cart_completion.call_count, 2)
            self.assertEqual(check_shop_address_completion.call_count, 2)
            self.assertEqual(check_shop_checkout_completion.call_count, 2)
            check_shop_payment_completion.assert_called_once()

    def test_redirect_on_price_change_on_payment(self):
        self.cart.partner_id.write(self.dummy_partner_address_values.copy())
        self.cart._set_delivery_method(self.free_delivery)

        self.pricelist.item_ids = [
            Command.create({"percent_price": 50, "compute_price": "percentage"})
        ]

        response = self.make_jsonrpc_request(
            f"/shop/payment/transaction/{self.cart.id}",
            params={
                "provider_id": self.provider.id,
                "payment_method_id": self.payment_method.id,
                "token_id": None,
                "flow": "direct",
                "tokenization_requested": False,
                "landing_route": "/shop/payment/validate",
                "access_token": self.cart._portal_ensure_token(),
            },
        )

        self.assertEqual(response["redirect"], "/shop/payment")
        self.assertIn("Prices have changed.", response["state_message"])
