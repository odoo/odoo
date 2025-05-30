# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import patch, tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.controllers.cart import Cart as CartController
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.models.sale_order import SaleOrder
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestCheckoutFlow(WebsiteSaleCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.write(cls.dummy_partner_address_values)
        cls.CheckoutController = CheckoutController()
        cls.CartController = CartController()

    def assertRedirectedTo(self, response, expected):
        self.assertEqual(response.status_code, 303, 'SEE OTHER')
        self.assertURLEqual(response.location, expected)

    def test_shop_warnings_are_cleared_after_being_displayed(self):
        self.cart.order_line = False  # An order line is required to go to checkout

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            # Assume the user is on the cart page and clicks on the "Checkout" button
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/shop/cart')

    def test_prior_checkout_error_are_shown_first(self):
        self.cart.order_line = False  # An order line is required to go to checkout
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_payment()

        self.assertRedirectedTo(response, '/shop/cart')  # Redirected back to the cart page first

    def test_impossible_to_checkout_without_a_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, path='/shop/checkout'):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/shop')

    def test_impossible_to_checkout_without_cart_in_draft(self):
        self.cart.action_confirm()

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/shop')

    def test_impossible_to_checkout_with_empty_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.empty_cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/shop/cart')

    def test_asked_to_login_if_account_on_checkout_mandatory(self):
        self.website.account_on_checkout = 'mandatory'

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/web/login?redirect=/shop/checkout')

    def test_impossible_to_checkout_with_public_partner(self):
        self.cart.partner_id = self.public_partner

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(response, '/shop/address')  # Must create a partner first

    def test_cart_must_have_a_billing_address(self):
        (
            self.cart.partner_shipping_id, self.cart.partner_invoice_id,
        ) = self.env['res.partner'].create([
            dict(self.dummy_partner_address_values, name='dummy', type='delivery'),
            # Invalid billing address
            dict(self.dummy_partner_address_values, name='dummy', type='invoice', email=False),
        ])

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(
            response,
            f'/shop/address?partner_id={self.cart.partner_invoice_id.id}&address_type=billing',
        )

    def test_cart_must_have_a_delivery_address(self):
        (
            self.cart.partner_shipping_id, self.cart.partner_invoice_id,
        ) = self.env['res.partner'].create([
            # Invalid delivery address
            dict(self.dummy_partner_address_values, name='dummy', type='delivery', email=False),
            # Invalid billing address
            dict(self.dummy_partner_address_values, name='dummy', type='invoice'),
        ])

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_checkout()

        self.assertRedirectedTo(
            response,
            f'/shop/address?partner_id={self.cart.partner_shipping_id.id}&address_type=delivery',
        )

    def test_impossible_to_confirm_if_no_delivery_method_available(self):
        self.env['delivery.carrier'].search([]).action_archive()
        self.env['delivery.carrier'].create({
            'name': 'Local BE',
            'country_ids': self.country_be.ids,
            'product_id': self.free_delivery.product_id.id,
        })
        self.cart.partner_shipping_id.country_id = self.country_us  # No DM can ship to the US
        self.cart.partner_shipping_id.state_id = self.country_us_state_id

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id,
        ):
            response = self.CheckoutController.shop_payment()

        # Customer must change his address of delivery
        self.assertRedirectedTo(response, '/shop/checkout')

    def test_impossible_to_confirm_if_no_delivery_method_is_selected(self):
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id,
        ):
            # Assume the user is on the checkout page and clicks on the "Confirm" button
            response = self.CheckoutController.shop_payment()

        self.assertRedirectedTo(response, '/shop/checkout')  # Redirected back to the checkout

    def test_warnings_cleared_when_visiting_shop_cart(self):
        website = self.website.with_user(self.public_user)
        with patch(
            'odoo.addons.website_sale.models.sale_order.SaleOrder._pop_shop_warnings',
            autospec=True, side_effect=SaleOrder._pop_shop_warnings,
        ) as pop_shop_warnings_mock:
            with MockRequest(
                website.env,
                website=website,
                path='/shop/checkout',
                sale_order_id=self.empty_cart.id,
            ):
                # Try to checkout with an empty cart
                self.assertRedirectedTo(self.CheckoutController.shop_checkout(), '/shop/cart')
                pop_shop_warnings_mock.assert_not_called()
                self.assertTrue(self.empty_cart.shop_warning)  # Empty cart warning

            with MockRequest(
                website.env, website=website, path='/shop/cart', sale_order_id=self.empty_cart.id,
            ):
                self.CartController.cart()

                # Warning displayed on the rendered cart page
                pop_shop_warnings_mock.assert_called_once()
                self.assertFalse(self.empty_cart.shop_warning)

    def test_warnings_cleared_when_visiting_shop_checkout(self):
        self.cart.carrier_id = False
        website = self.website.with_user(self.public_user)
        with patch(
            'odoo.addons.website_sale.models.sale_order.SaleOrder._pop_shop_warnings',
            autospec=True, side_effect=SaleOrder._pop_shop_warnings,
        ) as pop_shop_warnings_mock:
            with MockRequest(
                website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id,
            ):
                self.assertRedirectedTo(self.CheckoutController.shop_payment(), '/shop/checkout')
                pop_shop_warnings_mock.assert_not_called()
                self.assertTrue(self.cart.shop_warning)  # Delivery method missing warning

            with MockRequest(
                website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id,
            ):
                self.CheckoutController.shop_checkout()

                # Warning displayed on the rendered checkout page
                pop_shop_warnings_mock.assert_called_once()
                self.assertFalse(self.cart.shop_warning)
