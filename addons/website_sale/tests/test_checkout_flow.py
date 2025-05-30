# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import patch, tagged

from odoo.addons.website_sale.models.sale_order import SaleOrder
from odoo.addons.website_sale.tests.common_checkout import CheckoutCommon


@tagged('post_install', '-at_install')
class TestCheckoutFlow(CheckoutCommon):

    def setUp(self):
        super().setUp()
        self.default_address_values.pop('address_type')
        self.partner_shipping, self.partner_invoice = self.env['res.partner'].create([
            dict(self.default_address_values, type='delivery'),
            dict(self.default_address_values, type='delivery'),
        ])
        self.cart.partner_shipping_id = self.partner_shipping
        self.cart.partner_invoice_id = self.partner_invoice

    def test_shop_warnings_are_cleared_after_being_displayed(self):
        self.authenticate_with_cart(None, None)
        self.cart.order_line = False  # An order line is required to go to checkout

        with patch(
            'odoo.addons.website_sale.models.sale_order.SaleOrder._pop_shop_warnings',
            autospec=True, side_effect=SaleOrder._pop_shop_warnings,
        ) as pop_shop_warnings_mock:
            # Assume the user is on the cart page and clicks on the "Checkout" button
            response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop/cart')  # Redirected back to the cart
        pop_shop_warnings_mock.assert_called_once()
        self.assertFalse(self.cart.shop_warning)

    def test_prior_checkout_error_are_shown_first(self):
        self.authenticate_with_cart(None, None)
        self.cart.order_line = False  # An order line is required to go to checkout
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        response = self.url_open('/shop/confirm_order')

        self.assertURLEqual(response.url, '/shop/cart')  # Redirected back to the cart page first

    def test_impossible_to_checkout_without_a_cart(self):
        self.authenticate(None, None)

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop')

    def test_impossible_to_checkout_without_cart_in_draft(self):
        self.authenticate_with_cart(None, None)
        self.cart.action_confirm()

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop')

    def test_impossible_to_checkout_with_empty_cart(self):
        self.authenticate_with_cart(None, None, cart_id=self.empty_cart.id)

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop/cart')

    def test_asked_to_login_if_account_on_checkout_mandatory(self):
        self.website.account_on_checkout = 'mandatory'
        self.authenticate_with_cart(None, None)

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/web/login?redirect=/shop/checkout')

    def test_impossible_to_checkout_with_public_partner(self):
        self.authenticate_with_cart(None, None)
        self.cart.partner_id = self.public_partner

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(response.url, '/shop/address')  # Must create a partner first

    def test_cart_must_have_a_billing_address(self):
        self.authenticate_with_cart(None, None)
        self.partner_invoice.email = ''  # Invalid billing address

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(
            response.url,
            f'/shop/address?partner_id={self.partner_invoice.id}&address_type=billing',
        )

    def test_cart_must_have_a_delivery_address(self):
        self.authenticate_with_cart(None, None)
        self.partner_shipping.email = ''  # Invalid delivery address

        response = self.url_open('/shop/checkout')

        self.assertURLEqual(
            response.url,
            f'/shop/address?partner_id={self.partner_shipping.id}&address_type=delivery',
        )

    def test_impossible_to_confirm_if_no_delivery_method_available(self):
        self.env['delivery.carrier'].search([]).action_archive()
        self.env['delivery.carrier'].create({
            'name': 'Local BE',
            'country_ids': self.country_be.ids,
            'product_id': self.free_delivery.product_id.id,
        })
        self.authenticate_with_cart(None, None)
        self.partner_shipping.country_id = self.country_us  # No DM can ship to the US
        self.partner_shipping.state_id = self.country_us_state_id

        response = self.url_open('/shop/confirm_order')

        # Customer must change his address of delivery
        self.assertURLEqual(response.url, '/shop/checkout')

    def test_impossible_to_confirm_if_no_delivery_method_is_selected(self):
        self.authenticate_with_cart(None, None)
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        # Assume the user is on the checkout page and clicks on the "Confirm" button
        response = self.url_open('/shop/confirm_order')

        self.assertURLEqual(response.url, '/shop/checkout')  # Redirected back to the checkout
