# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from uuid import uuid4
from unittest.mock import Mock, patch
from werkzeug import urls

from odoo import Command
from odoo.http import root
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_sale.controllers.delivery import WebsiteSaleDelivery as WebsiteSaleDeliveryController
from odoo.addons.website_sale.controllers.main import WebsiteSale


@tagged('post_install', '-at_install')
class TestWebsiteSaleDeliveryExpressCheckoutFlows(HttpCaseWithUserDemo):
    """ The goal of this method class is to test the address management on
        express checkout.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref('website.default_website')
        cls.country_id = cls.env.ref('base.be').id
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.website.user_id.partner_id.id,
            'website_id': cls.website.id,
            'order_line': [Command.create({
                'product_id': cls.env['product.product'].create({
                    'name': 'Product A',
                    'list_price': 100,
                    'website_published': True,
                    'sale_ok': True}).id,
                'name': 'Product A',
            })]
        })
        cls.rate_shipment_result = {
            'success': True,
            'price': 5.0,
            'warning_message': '',
        }
        cls.express_checkout_billing_values = {
            'name': 'Express Checkout Partner',
            'email': 'express@check.out',
            'phone': '0000000000',
            'street': 'ooo',
            'street2': 'ppp',
            'city': 'ooo',
            'zip': '1200',
            'country': 'US',
            'state': 'AL',
        }
        cls.express_checkout_shipping_values = {
            'name': 'Express Checkout Shipping Partner',
            'email': 'express_shipping@check.out',
            'phone': '1111111111',
            'street': 'ooo shipping',
            'street2': 'ppp shipping',
            'city': 'ooo shipping',
            'zip': '25781',
            'country': 'US',
            'state': 'WA',
        }
        cls.express_checkout_anonymized_shipping_values = {
            'city': 'ooo shipping',
            'zip': '25781',
            'country': 'US',
            'state': 'WA',
        }
        cls.express_checkout_anonymized_shipping_values_2 = {
            'city': 'ooo shipping 2',
            'zip': '91200',
            'country': 'US',
            'state': 'AL',
        }
        # Ensure demo user address exists and is valid
        cls.user_demo.write({
            'street': "215 Vine St",
            'city': "Scranton",
            'zip': "18503",
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
        })

    def setUp(self):
        super().setUp()
        self.express_checkout_demo_shipping_values = {
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
        self.express_checkout_anonymized_demo_shipping_values = {
            'city': self.user_demo.partner_id.city,
            'zip': self.user_demo.partner_id.zip,
            'country': self.user_demo.partner_id.country_id.code,
            'state': self.user_demo.partner_id.state_id.code,
        }
        self.express_checkout_demo_shipping_values_2 = {
            'name': 'Express Checkout Shipping Partner',
            'email': 'express_shipping@check.out',
            'phone': '1111111111',
            'street': 'ooo shipping',
            'street2': 'ppp shipping',
            'city': self.user_demo.partner_id.city,
            'zip': self.user_demo.partner_id.zip,
            'country': self.user_demo.partner_id.country_id.code,
            'state': self.user_demo.partner_id.state_id.code,
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values)
                }
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values)
                }
            )
            new_partner = self.sale_order.partner_shipping_id
            self.make_jsonrpc_request(
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values_2)
                }
            )
            self.assertEqual(new_partner.id, self.sale_order.partner_shipping_id.id)
            self.assertPartnerShippingValues(
                new_partner,
                self.express_checkout_anonymized_shipping_values_2,
            )

    def test_express_checkout_registered_user_exisiting_shipping_address_change(self):
        """ Test that when using express checkout as a registered user and selecting an exisiting
            shipping address, the existing partner (the one of the so) is reused.
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values)
                }
            )
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

    def test_express_checkout_registered_user_new_shipping_address_change(self):
        """ Test that when using express checkout as a registered user and selecting a new shipping
            address, a new partner is created if the partner of the SO or his children are different
            than the delivery information received.
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values)
                }
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values)
                }
            )
            new_partner = self.sale_order.partner_shipping_id
            self.make_jsonrpc_request(
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_shipping_values_2)
                }
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
            # Since we didn't mock the product ids for the mocked carrier, we return an unsuccessful
            # response to skip the part where the product ids are checked on the carrier.
            return_value=dict(self.rate_shipment_result, **{'success': False})
        )

        WebsiteSaleDeliveryController._get_rate(
            delivery_carrier_mock, self.sale_order, is_express_checkout_flow=True
        )
        sale_order = delivery_carrier_mock.rate_shipment.call_args[0][0]
        self.assertTrue(sale_order._context.get('express_checkout_partial_delivery_address'))

    def test_express_checkout_registered_user_with_shipping_option(self):
        """ Test that when you use the express checkout as a registered user and the shipping
            address sent by the express checkout form exactly matches to one of the addresses linked
            to this user in odoo, we do not create a new partner and reuse the existing one.
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
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_demo_shipping_values)
                }
            )
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

            self.make_jsonrpc_request(urls.url_join(self.base_url(), WebsiteSale._express_checkout_route), params={
                'billing_address': dict(self.express_checkout_billing_values),
                'shipping_address': dict(self.express_checkout_demo_shipping_values),
                'shipping_option': shipping_options[0],
            })
            self.assertEqual(self.sale_order.partner_id.id, self.user_demo.partner_id.id)

    def test_express_checkout_registered_user_with_shipping_option_new_address(self):
        """ Test that when you use the express checkout as a registered user and the shipping
            address sent by the express checkout form doesn't exist in odoo, we create a new partner.
        """
        self.sale_order.partner_id = self.user_demo.partner_id.id
        session = self.authenticate(self.user_demo.login, self.user_demo.login)
        session['sale_order_id'] = self.sale_order.id
        root.session_store.save(session)
        with patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value=self.rate_shipment_result
        ):
            # Won't create a new partner because the partial information are the same the an
            # exisiting partner linked to the SO
            shipping_options = self.make_jsonrpc_request(
                urls.url_join(
                    self.base_url(), WebsiteSaleDeliveryController._express_checkout_shipping_route
                ), params={
                    'partial_shipping_address': dict(self.express_checkout_anonymized_demo_shipping_values)
                }
            )
            self.assertEqual(self.sale_order.partner_shipping_id, self.user_demo.partner_id)

            # Will create a new partner because the complete shipping information are different than
            # the partner actually selected.
            self.make_jsonrpc_request(
                urls.url_join(
                    self.base_url(),
                    WebsiteSaleDeliveryController._express_checkout_route
                ), params={
                    'billing_address': dict(self.express_checkout_billing_values),
                    'shipping_address': dict(self.express_checkout_demo_shipping_values_2),
                    'shipping_option': shipping_options[0],
                }
            )
            self.assertNotEqual(
                self.sale_order.partner_shipping_id.id, self.user_demo.partner_id.id
            )
            self.assertFalse(
                self.sale_order.partner_shipping_id.name.endswith(self.sale_order.name)
            )
