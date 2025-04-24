# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock, patch

from odoo.http import root
from odoo.tests import HttpCase, tagged
from odoo.tools import urls

from odoo.addons.payment import utils as payment_utils
from odoo.addons.website_sale.controllers.delivery import Delivery as WebsiteSaleDeliveryController
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.cart import Cart
from odoo.addons.website_sale.tests.common import MockRequest, WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleExpressCheckoutFlows(WebsiteSaleCommon, HttpCase):
    """ The goal of this method class is to test the address management on
        express checkout.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_id = cls.country_be.id
        cls.sale_order = cls.cart
        cls.sale_order.partner_id = cls.public_partner.id
        cls.express_checkout_billing_values = {
            'name': 'Express Checkout Partner',
            'email': 'express@check.out',
            'phone': '0000000000',
            'street': 'ooo',
            'street2': 'ppp',
            'city': 'ooo',
            'zip': '1200',
            'country': "US",  # United States
            'state': "CA",  # California
        }
        cls.express_checkout_shipping_values = {
            'name': "Express Checkout Shipping Partner",
            'email': "express_shipping@check.out",
            'phone': "1111111111",
            'street': "ooo shipping",
            'street2': "ppp shipping",
            'city': "ooo shipping",
            'zip': "25781",
            'country': "US",  # United States
            'state': "WA",  # Washington
        }
        cls.express_checkout_anonymized_shipping_values = {
            'city': "ooo shipping",
            'zip': "6155",
            'country': "AU",  # Australia
            'state': "WA",  # Western Australia
        }
        cls.express_checkout_anonymized_shipping_values_2 = {
            'city': "ooo shipping 2",
            'zip': "11519",
            'country': "ES",  # Spain
            'state': "CA",  # Cádiz
        }

        cls.user_demo = cls._create_new_internal_user(**cls.dummy_partner_address_values)

        cls.express_checkout_demo_shipping_values = {
            'name': cls.user_demo.partner_id.name,
            'email': cls.user_demo.partner_id.email,
            'phone': cls.user_demo.partner_id.phone,
            'street': cls.user_demo.partner_id.street,
            'street2': cls.user_demo.partner_id.street2,
            'city': cls.user_demo.partner_id.city,
            'zip': cls.user_demo.partner_id.zip,
            'country': cls.user_demo.partner_id.country_id.code,
            'state': cls.user_demo.partner_id.state_id.code,
        }
        cls.express_checkout_anonymized_demo_shipping_values = {
            'city': cls.user_demo.partner_id.city,
            'zip': cls.user_demo.partner_id.zip,
            'country': cls.user_demo.partner_id.country_id.code,
            'state': cls.user_demo.partner_id.state_id.code,
        }
        cls.express_checkout_demo_shipping_values_2 = {
            'name': "Express Checkout Shipping Partner",
            'email': "express_shipping@check.out",
            'phone': "1111111111",
            'street': "ooo shipping",
            'street2': "ppp shipping",
            'city': cls.user_demo.partner_id.city,
            'zip': cls.user_demo.partner_id.zip,
            'country': cls.user_demo.partner_id.country_id.code,
            'state': cls.user_demo.partner_id.state_id.code,
        }
        cls.rate_shipment_result = {
            'success': True,
            'price': 5.0,
            'warning_message': "",
        }

    def assertPartnerShippingValues(self, partner, shipping_values):
        for key, expected in shipping_values.items():
            if key in ('state', 'country'):
                value = partner[f'{key}_id'].code
            else:
                value = partner[key]
            self.assertEqual(value, expected, "Shipping value should match")
        if partner.state_id:
            self.assertEqual(
                partner.state_id.country_id,
                partner.country_id,
                "Partner's state should be within partner's country",
            )

    def test_express_checkout_takes_order_amount_without_delivery(self):
        """Test that the amount to pay does not include the delivery costs in express checkout."""
        amount_without_delivery = payment_utils.to_minor_currency_units(
            self.cart.amount_total, self.cart.currency_id
        )
        self.carrier.fixed_price = 20
        self.cart.set_delivery_line(self.carrier, self.carrier.fixed_price)
        with MockRequest(self.env, sale_order_id=self.cart.id, website=self.website):
            payment_values = Cart()._get_express_shop_payment_values(self.cart)

        self.assertEqual(payment_values['minor_amount'], amount_without_delivery)

    def test_express_checkout_public_user(self):
        """ Test that when using express checkout as a public user, a new partner is created. """
        session = self.authenticate(None, None)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)

        self.make_jsonrpc_request(
            urls.urljoin(
                self.base_url(), WebsiteSale._express_checkout_route
            ), params={
                'billing_address': dict(self.express_checkout_billing_values)
            }
        )

        new_partner = self.sale_order.partner_id
        self.assertNotEqual(new_partner, self.website.user_id.partner_id)
        self.assertPartnerShippingValues(
            new_partner,
            self.express_checkout_billing_values,
        )

    def test_express_checkout_registered_user(self):
        """ Test that when you use express checkout as a registered user and the address sent by the
            express checkout form exactly matches the one registered in odoo, we do not create a new
            partner and reuse the existing one.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)

        self.make_jsonrpc_request(
            urls.urljoin(
                self.base_url(), WebsiteSale._express_checkout_route
            ), params={
                'billing_address': {
                    'name': self.user_demo.partner_id.name,
                    'email': self.user_demo.partner_id.email,
                    'phone': self.user_demo.partner_id.phone,
                    'street': self.user_demo.partner_id.street,
                    'street2': self.user_demo.partner_id.street2,
                    'city': self.user_demo.partner_id.city,
                    'zip': self.user_demo.partner_id.zip,
                    'country': self.user_demo.partner_id.country_id.code,
                    'state': self.user_demo.partner_id.state_id.code,
                }
            }
        )

        self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)
        self.assertEqual(self.sale_order.partner_invoice_id.id, self.user_demo.partner_id.id)

    def test_express_checkout_registered_user_existing_address(self):
        """ Test that when you use the express checkout as a registered user and the address sent by
            the express checkout form exactly matches to one of the addresses linked to this user in
            odoo, we do not create a new partner and reuse the existing one.
        """
        # Create a child partner for the demo partner
        child_partner_address = dict(self.express_checkout_billing_values)
        child_partner_country = self.env['res.country'].search([
            ('code', '=', child_partner_address.pop('country')),
        ], limit=1)
        child_partner_state = self.env['res.country.state'].search([
            ('code', '=', child_partner_address.pop('state')),
            ('country_id', '=', child_partner_country.id),
        ], limit=1)
        child_partner = self.env['res.partner'].create(dict(
            **child_partner_address,
            parent_id=self.user_demo.partner_id.id,
            type='invoice',
            country_id=child_partner_country.id,
            state_id=child_partner_state.id,
        ))

        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)

        self.make_jsonrpc_request(
            urls.urljoin(
                self.base_url(), WebsiteSale._express_checkout_route
            ), params={
                'billing_address': dict(self.express_checkout_billing_values)
            }
        )

        self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)
        self.assertEqual(self.sale_order.partner_invoice_id.id, child_partner.id)

    def test_express_checkout_registered_user_new_address(self):
        """ Test that when you use the express checkout as a registered user and the address sent by
            the express checkout form doesn't match to one of the addresses linked to this user in
            odoo, we create a new partner.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)

        self.make_jsonrpc_request(
            urls.urljoin(
                self.base_url(), WebsiteSale._express_checkout_route
            ), params={
                'billing_address': dict(self.express_checkout_billing_values)
            }
        )

        self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)
        new_partner = self.sale_order.partner_invoice_id
        self.assertNotEqual(new_partner, self.website.user_id.partner_id)
        self.assertPartnerShippingValues(
            new_partner,
            self.express_checkout_billing_values,
        )

    def test_express_checkout_public_user_shipping_address_change(self):
        """ Test that when using express checkout as a public user and selecting a shipping address,
            a new partner is created if the partner of the SO is the public partner.
        """
        session = self.authenticate(None, None)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values,
                    ),
                },
            )
            new_partner = self.sale_order.partner_shipping_id
            self.assertNotEqual(new_partner, self.website.user_id.partner_id)
            self.assertTrue(new_partner.name.endswith(self.sale_order.name))
            self.assertPartnerShippingValues(
                new_partner,
                self.express_checkout_anonymized_shipping_values,
            )

    def test_express_checkout_public_user_shipping_address_change_twice(self):
        """ Test that when using express checkout as a public user and selecting a shipping address
            more than once, a new partner is created if the partner of the SO is the public partner
            (only creates one new partner that is updated).
        """
        session = self.authenticate(None, None)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values,
                    ),
                },
            )
            new_partner = self.sale_order.partner_shipping_id
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values_2,
                    ),
                },
            )
            self.assertEqual(new_partner.id, self.sale_order.partner_shipping_id.id)
            self.assertPartnerShippingValues(
                new_partner,
                self.express_checkout_anonymized_shipping_values_2,
            )

    def test_express_checkout_registered_user_exisiting_shipping_address_change(self):
        """ Test that when using express checkout as a registered user and selecting an exisiting
            shipping address, the existing partner (the one of the SO) is reused.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values,
                    ),
                },
            )
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

    def test_express_checkout_registered_user_new_shipping_address_change(self):
        """ Test that when using express checkout as a registered user and selecting a new shipping
            address, a new partner is created if the partner of the SO or his children are different
            from the delivery information received.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values,
                    ),
                },
            )
            new_partner = self.sale_order.partner_shipping_id
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)
            self.assertNotEqual(new_partner.id, self.user_demo.partner_id.id)
            self.assertTrue(new_partner.name.endswith(self.sale_order.name))
            self.assertPartnerShippingValues(
                new_partner,
                self.express_checkout_anonymized_shipping_values,
            )

    def test_express_checkout_registered_user_new_shipping_address_change_twice(self):
        """ Test that when using express checkout as a registered user and selecting a new
            shipping address more than once, a new partner is created if the partner of the SO is
            the public partner (only creates one new partner that is updated).
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values,
                    ),
                },
            )
            new_partner = self.sale_order.partner_shipping_id
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_shipping_values_2,
                    ),
                },
            )
            self.assertEqual(new_partner.id, self.sale_order.partner_shipping_id.id)
            self.assertPartnerShippingValues(
                new_partner,
                self.express_checkout_anonymized_shipping_values_2
            )

    def test_express_checkout_partial_delivery_address_context_key(self):
        """ Test that when using express checkout with only partial delivery information,
            `express_checkout_partial_delivery_address` context key is in the context.
        """
        delivery_carrier_mock = Mock()
        delivery_carrier_mock.rate_shipment = Mock(
            # Since we didn't mock the product ids for the mocked carrier, return an unsuccessful
            # response to skip the part where the product ids are checked on the carrier
            return_value=dict(self.rate_shipment_result, success=False)
        )

        WebsiteSaleDeliveryController._get_rate(
            delivery_carrier_mock, self.sale_order, is_express_checkout_flow=True
        )
        sale_order = delivery_carrier_mock.rate_shipment.call_args[0][0]
        self.assertTrue(sale_order.env.context.get('express_checkout_partial_delivery_address'))

    def test_express_checkout_registered_user_with_shipping_option(self):
        """ Test that when you use the express checkout as a registered user and the shipping
            address sent by the express checkout form exactly matches one of the addresses linked
            to this user in Odoo, we do not create a new partner and reuse the existing one.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            shipping_options = self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_demo_shipping_values,
                    ),
                },
            )
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_route,
                ),
                params={
                    'billing_address': dict(self.express_checkout_billing_values),
                    'shipping_address': dict(self.express_checkout_demo_shipping_values),
                    'shipping_option': shipping_options['delivery_methods'][0],
                },
            )
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

    def test_express_checkout_registered_user_with_shipping_option_new_address(self):
        """ Test that when you use the express checkout as a registered user and the shipping
            address sent by the express checkout form doesn't exist in Odoo, we create a new
            partner.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            # Won't create a new partner because the partial information are the same as an
            # exisiting partner linked to the SO
            shipping_options = self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_delivery_route,
                ),
                params={
                    'partial_delivery_address': dict(
                        self.express_checkout_anonymized_demo_shipping_values,
                    ),
                },
            )
            self.assertEqual(self.sale_order.partner_shipping_id, self.user_demo.partner_id)

            # Will create a new partner because the complete shipping information differs from
            # the partner actually selected
            self.make_jsonrpc_request(
                urls.urljoin(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_route
                ),
                params={
                    'billing_address': dict(self.express_checkout_billing_values),
                    'shipping_address': dict(self.express_checkout_demo_shipping_values_2),
                    'shipping_option': shipping_options['delivery_methods'][0],
                },
            )
            self.assertNotEqual(
                self.sale_order.partner_shipping_id.id, self.user_demo.partner_id.id
            )
            self.assertFalse(
                self.sale_order.partner_shipping_id.name.endswith(self.sale_order.name)
            )
