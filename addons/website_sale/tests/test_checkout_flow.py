# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.http.router import root
from odoo.tests import patch, tagged
from odoo.tests.common import HttpCase

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.website_sale.controllers.cart import Cart as CartController
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.controllers.payment import PaymentPortal as PaymentController
from odoo.addons.website_sale.models.website import CART_SESSION_CACHE_KEY
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestCheckoutFlow(WebsiteSaleCommon, PaymentCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.write(cls.dummy_partner_address_values)
        cls.CheckoutController = CheckoutController()
        cls.CartController = CartController()
        cls.PaymentController = PaymentController()

    def assert_redirected_to(self, response, expected):
        self.assertEqual(response.status_code, 303, 'SEE OTHER')
        self.assertURLEqual(response.location, expected)

    def test_checkout_step_validation_redirects_to_the_first_invalid_step(self):
        self.cart.order_line = False  # An order line is required to go to checkout
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_payment()

        self.assert_redirected_to(response, '/shop/cart')  # Redirected back to the cart page first

    def test_impossible_to_checkout_without_a_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, path='/shop/checkout'):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, '/shop')

    def test_impossible_to_checkout_without_cart_in_draft(self):
        self.cart.action_confirm()

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, '/shop')

    def test_impossible_to_checkout_with_empty_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.empty_cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, '/shop/cart')

    def test_asked_to_login_if_account_on_checkout_mandatory(self):
        self.website.account_on_checkout = 'mandatory'

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, '/web/login?redirect=/shop/checkout')

    def test_impossible_to_checkout_with_public_partner(self):
        self.cart.partner_id = self.public_partner

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(response, '/shop/address')  # Must create a partner first

    def test_cart_must_have_a_billing_address(self):
        (self.cart.partner_shipping_id, self.cart.partner_invoice_id) = self.env[
            'res.partner'
        ].create([
            dict(
                self.dummy_partner_address_values,
                name='dummy',
                type='delivery',
                parent_id=self.partner.id,
            ),
            # Invalid billing address
            dict(
                self.dummy_partner_address_values,
                name='dummy',
                type='invoice',
                parent_id=self.partner.id,
                email=False,
            ),
        ])

        self.assertFalse(self.cart.partner_invoice_id.email)
        self.assertIn(self.cart.partner_shipping_id, self.cart.partner_id.child_ids)
        self.assertIn(self.cart.partner_invoice_id, self.cart.partner_id.child_ids)

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(
            response,
            f'/shop/address?partner_id={self.cart.partner_invoice_id.id}&address_type=billing',
        )

    def test_cart_must_have_a_delivery_address(self):
        (self.cart.partner_shipping_id, self.cart.partner_invoice_id) = self.env[
            'res.partner'
        ].create([
            # Invalid delivery address
            dict(
                self.dummy_partner_address_values,
                name='dummy',
                type='delivery',
                parent_id=self.partner.id,
                email=False,
            ),
            # Invalid billing address
            dict(
                self.dummy_partner_address_values,
                name='dummy',
                type='invoice',
                parent_id=self.partner.id,
            ),
        ])

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/checkout', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_checkout()

        self.assert_redirected_to(
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
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id
        ):
            response = self.CheckoutController.shop_payment()

        # Customer must change his address of delivery
        self.assert_redirected_to(response, '/shop/checkout')

    def test_impossible_to_confirm_if_no_delivery_method_is_selected(self):
        self.cart.carrier_id = False  # A delivery method is required to confirm the order

        website = self.website.with_user(self.public_user)
        with MockRequest(
            website.env, website=website, path='/shop/payment', sale_order_id=self.cart.id
        ):
            # Assume the user is on the checkout page and clicks on the "Confirm" button
            response = self.CheckoutController.shop_payment()

        self.assert_redirected_to(response, '/shop/checkout')  # Redirected back to the checkout

    def test_alerts_cleared_when_rendering_a_checkout_step(self):
        session = self.authenticate(None, None)
        session[CART_SESSION_CACHE_KEY] = self.cart.id
        root.session_store.save(session)

        with patch(
            'odoo.addons.website_sale.models.sale_order.SaleOrder._clear_alerts', autospec=True
        ) as clear_alerts_mock:
            self.url_open('/shop/cart')

            clear_alerts_mock.assert_called_once()

    def test_final_payment_step_check_all_checkout_steps(self):
        session = self.authenticate(None, None)
        session[CART_SESSION_CACHE_KEY] = self.cart.id
        root.session_store.save(session)

        with (
            patch(
                'odoo.addons.website_sale.controllers.main.WebsiteSale._check_post_shop_cart_step',
                return_value=None,
            ) as _check_post_shop_cart_step,
            patch(
                'odoo.addons.website_sale.controllers.main.WebsiteSale._check_post_shop_address_step',
                return_value=None,
            ) as _check_post_shop_address_step,
            patch(
                'odoo.addons.website_sale.controllers.main.WebsiteSale._check_post_shop_checkout_step',
                return_value=None,
            ) as _check_post_shop_checkout_step,
        ):
            self.url_open('/shop/payment')

            _check_post_shop_cart_step.assert_called_once()
            _check_post_shop_address_step.assert_called_once()
            _check_post_shop_checkout_step.assert_called_once()
            self.assertEqual(
                _check_post_shop_checkout_step.call_args[1],
                {},
                'block_on_price_change should not be truthy when loading the payment page',
            )

            self.make_jsonrpc_request(
                f'/shop/payment/transaction/{self.cart.id}',
                params={
                    'provider_id': self.provider.id,
                    'payment_method_id': self.payment_method.id,
                    'token_id': None,
                    'flow': 'direct',
                    'tokenization_requested': False,
                    'landing_route': '/shop/payment/validate',
                    'access_token': self.cart._portal_ensure_token(),
                },
            )

            self.assertEqual(_check_post_shop_cart_step.call_count, 2)
            self.assertEqual(_check_post_shop_address_step.call_count, 2)
            self.assertEqual(_check_post_shop_checkout_step.call_count, 2)
            self.assertEqual(
                _check_post_shop_checkout_step.call_args[1],
                {'block_on_price_change': True},
                'price changes should be blocking when starting the payment',
            )

    def test_redirect_on_price_change_on_payment(self):
        session = self.authenticate(None, None)
        session[CART_SESSION_CACHE_KEY] = self.cart.id
        root.session_store.save(session)

        self.cart.set_delivery_line(self.carrier, 0.0)

        self.pricelist.item_ids = [
            Command.create({'percent_price': 50, 'compute_price': 'percentage'})
        ]

        response = self.make_jsonrpc_request(
            f'/shop/payment/transaction/{self.cart.id}',
            params={
                'provider_id': self.provider.id,
                'payment_method_id': self.payment_method.id,
                'token_id': None,
                'flow': 'direct',
                'tokenization_requested': False,
                'landing_route': '/shop/payment/validate',
                'access_token': self.cart._portal_ensure_token(),
            },
        )

        self.assertEqual(response['redirect'], '/shop/payment')  # Redirected back to the checkout
