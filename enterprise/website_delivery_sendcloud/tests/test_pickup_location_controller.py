# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import requests
import json

from unittest.mock import patch
from contextlib import contextmanager
from odoo import api
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website.tools import MockRequest
from odoo.tests import TransactionCase, tagged


@contextmanager
def _mock_call():
    def _mock_request(*args, **kwargs):
        method = kwargs.get('method') or args[0]
        url = kwargs.get('url') or args[1]
        responses = {
            'get': {
                'service-points': [{
                    'id': 11238037,
                    'name': 'STATION AVIA',
                    'formatted_opening_times': {
                        '0': ['07:00 - 18:30'],
                        '1': ['07:00 - 18:30'],
                        '2': ['07:00 - 18:30'],
                        '3': ['07:00 - 18:30'],
                        '4': ['08:00 - 14:00', '15:00 - 18:00'],
                        '5': ['09:00 - 16:00'],
                        '6': [],
                    },
                    'street': 'CHAUSSEE DE NAMUR',
                    'house_number': '67',
                    'city': 'RAMILLIES',
                    'postal_code': '1367',
                    'country': 'BE',
                    'latitude': '50.634529',
                    'longitude': '4.864696',
                }],
            },
            'post': {
            }
        }

        for endpoint, content in responses[method].items():
            if endpoint in url:
                response = requests.Response()
                response._content = json.dumps(content).encode()
                response.status_code = 200
                return response

        raise Exception('unhandled request url %s' % url)

    with patch.object(requests.Session, 'request', _mock_request):
        yield


@tagged('post_install', '-at_install')
class TestWebsiteDeliverySendcloudLocationsController(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.WebsiteSaleController = WebsiteSale()
        cls.website = cls.env.ref('website.default_website')
        cls.your_company = cls.env.ref("base.main_partner")
        cls.warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.your_company.id)], limit=1)
        cls.your_company.write({'name': 'Odoo SA',
                                'country_id': cls.env.ref('base.be').id,
                                'street': 'Chaussée de Namur 40',
                                'street2': False,
                                'state_id': False,
                                'city': 'Ramillies',
                                'zip': 1367,
                                'email': 'odoo@example.com',
                                'phone': '081813700',
                                })
        # partner will be in europe
        cls.eu_partner = cls.env['res.partner'].create({
            'name': 'newPartner',
            'country_id': cls.env.ref('base.be').id,
            'zip': '1367',
            'state_id': False,
            'country_code': 'BE',
            'street': 'Rue des Bourlottes 9',
            'city': 'Ramillies'
        })

        cls.product_to_ship1 = cls.env["product.product"].create({
            'name': 'Door with wings',
            'type': 'consu',
            'weight': 10.0,
            'sale_ok': True,
            'website_published': True,
            'lst_price': 1000.0,
            'standard_price': 800.0,
        })

        shipping_product = cls.env['product.product'].create({
            'name': 'SendCloud Delivery',
            'type': 'service'
        })

        uom = cls.env.ref('uom.product_uom_meter')

        # Allow customization of 'sendcloud_use_locations' on the delivery_carrier
        cls.sendcloud_shipping = cls.env['sendcloud.shipping.product'].create({
                'name': 'Test product',
                'sendcloud_code': 'test',
                'carrier': 'Test',
                'min_weight': 1,
                'max_weight': 50001,
                'functionalities': {
                    'bool_func': [],
                    'detail_func': {},
                    'customizable': {
                        'last_mile': [
                            'service_point',
                            'home_delivery',
                        ]
                    },
                },
        })

        cls.sendcloud = cls.env['delivery.carrier'].create({
            'delivery_type': 'sendcloud',
            'product_id': shipping_product.id,
            'sendcloud_public_key': 'mock_key',
            'sendcloud_secret_key': 'mock_key',
            'name': 'SendCloud',
            'sendcloud_locations_radius_value': 1000,
            'sendcloud_locations_radius_unit': uom.id,
            'sendcloud_locations_id': 1,
            'sendcloud_shipping_id': cls.sendcloud_shipping.id,
        })

        cls.sendcloud.sendcloud_use_locations = True
        cls.payment_provider = cls.env['payment.provider'].create({'name': 'test'})

        cls.payment_method_id = cls.env.ref('payment.payment_method_unknown').id

        cls.partner = cls.env['res.partner'].create({'name': 'testestset'})

        cls.currency = cls.env['res.currency'].create({'name': 'testestset', 'symbol': '€'})

        cls.transaction = cls.env['payment.transaction'].create({
            'state': 'draft',
            'provider_id': cls.payment_provider.id,
            'payment_method_id': cls.payment_method_id,
            'partner_id': cls.partner.id,
            'currency_id': cls.currency.id,
            'amount': 42
        })

        cls.order = cls.env['sale.order'].create({
            'carrier_id': cls.sendcloud.id,
            'partner_id': cls.env.user.partner_id.id,
            'partner_shipping_id': cls.eu_partner.id,
            'transaction_ids': [cls.transaction.id]
        })

    def test_controller_pickup_location(self):
        with MockRequest(self.env, website=self.website, sale_order_id=self.order.id):
            with _mock_call():
                response = Delivery().website_sale_get_pickup_locations()
                self.assertNotEqual({},
                    Delivery().website_sale_set_pickup_location(
                        pickup_location_data=json.dumps(response['pickup_locations'][0])
                    )
                )
                self.assertEqual({
                    'id': 11238037,
                    'name': 'Station Avia',
                    'opening_hours': {
                        '0': ['07:00 - 18:30'],
                        '1': ['07:00 - 18:30'],
                        '2': ['07:00 - 18:30'],
                        '3': ['07:00 - 18:30'],
                        '4': ['08:00 - 14:00', '15:00 - 18:00'],
                        '5': ['09:00 - 16:00'],
                        '6': [],
                    },
                    'street': 'Chaussee De Namur 67',
                    'city': 'Ramillies',
                    'zip_code': '1367',
                    'country_code': 'BE',
                    'latitude': '50.634529',
                    'longitude': '4.864696',
                }, self.order.pickup_location_data)

    def test_sendcloud_delivery_partner(self):
        """
        Test that the delivery associated to a website sale using a sendcloud
        pickup point is associated with a partner of `delivery` type.
        """
        product = self.product_to_ship1
        public_user = self.env.ref('base.public_user')
        website = self.website.with_user(public_user)
        with MockRequest(product.with_user(public_user).env, website=website):
            self.WebsiteSaleController.cart_update_json(product_id=product.id, add_qty=1)
            sale_order = website.sale_get_order()
        partner_address = {
            'name': 'Bob',
            'email': 'bob@email.com',
            'phone': '+1 555-555-555',
            'street': 'Chaussee De Namur 65',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': self.ref('base.be'),
        }
        env = api.Environment(self.env.cr, public_user.id, {})
        with MockRequest(self.env, website=website.with_user(public_user).with_env(env), sale_order_id=sale_order.id) as req:
            req.httprequest.method = "POST"
            self.WebsiteSaleController.shop_address_submit(**partner_address)
        sale_order.write({
            'carrier_id': self.sendcloud.id,
            'transaction_ids': [self.transaction.id],
        })
        with MockRequest(self.env, website=website, sale_order_id=sale_order.id):
            with _mock_call():
                response = Delivery().website_sale_get_pickup_locations()
                Delivery().website_sale_set_pickup_location(
                        pickup_location_data=json.dumps(response['pickup_locations'][0])
                    )
        sale_order.action_confirm()
        # the delivery adress of the SO and the delivery should have been updated
        # to gather the mail and phon number of the partner but the pickup point address
        delivery = sale_order.picking_ids
        self.assertEqual(sale_order.partner_shipping_id, delivery.partner_id)
        self.assertRecordValues(delivery.partner_id, [{
            'type': 'delivery',
            'name': 'Station Avia',
            'contact_address_complete': 'Chaussee De Namur 67, 1367 Ramillies, Belgium',
            'email': 'bob@email.com',
            'phone': '+1 555-555-555',
        }])
        sendcloud_class = 'odoo.addons.delivery_sendcloud.models.sendcloud_service.SendCloud'

        def _prepare_fake_parcel(self, *args, **kwargs):
            res = {
                'id': 420277401,
                'reference': '0',
                'status': {'id': 1000, 'message': 'Ready to send'},
                'tracking_number': '323211588559959039950037',
                'weight': '10.0',
                'order_number': 'S00404',
                'total_insured_value': 0,
                'parcel_items': [{}],
                'documents': [],
                'external_reference': None,
                'is_return': False,
                'note': '',
                'total_order_value': '1210',
                'total_order_value_currency': 'EUR',
                'length': '0.00',
                'width': '0.00',
                'height': '0.00',
                'contract': 519,
                'address_divided': {'street': 'Chaussee De Namur', 'house_number': '65'},
                'shipment': {'id': 95, 'name': 'bpost @bpack 0-10kg'},
                'shipping_method': 95,
                'shipping_method_checkout_name': 'bpost @bpack',
                'insured_value': 0,
                'shipment_uuid': None,
                'data': {},
                'type': 'parcel',
                'external_order_id': '420277401',
                'external_shipment_id': '',
                'colli_uuid': '925023d1-d4cc-4774-9ea3-c1ecb152a6e0',
                'collo_nr': 0, 'collo_count': 1,
                'label': {'normal_printer': [], 'label_printer': 'https://panel.sendcloud.sc/api/v2/labels/label_printer/420277401'},
                'customs_declaration': {},
                'to_state': None,
                'date_created': '07-10-2024 14:12:12',
                'date_announced': '07-10-2024 14:12:13',
                'date_updated': '07-10-2024 14:12:13',
                'customs_shipment_type': 2,
                'address': 'Chaussee De Namur 65',
                'address_2': '',
                'city': 'Ramillies',
                'company_name': '',
                'country': {'iso_2': 'BE', 'iso_3': 'BEL', 'name': 'Belgium'},
                'email': 'bob@email.com',
                'name': 'Bob',
                'postal_code': '1367',
                'telephone': '+1 555-555-555',
                'to_post_number': '',
                'to_service_point': 11238037,
                'errors': {},
                'carrier': {'code': 'bpost'},
                'tracking_url': 'https://tracking.eu-central-1-0.sendcloud.sc/fake',
            }
            parcel_common = self._prepare_parcel_common_data(picking=delivery, is_return=False, sender_id=False)
            for key, value in parcel_common.items():
                if key in res and value:
                    res[key] = value
            return [res]

        def _get_fake_shipping_rate(*args, **kwargs):
            return [5.0]

        def _fake_cancel_shipment(*args, **kwargs):
            return {'status': 'queued', 'message': 'Parcel cancellation has been queued'}

        with (
            patch(sendcloud_class + '._send_shipment', new=_prepare_fake_parcel),
            patch(sendcloud_class + '._get_shipping_rate', new=_get_fake_shipping_rate),
            patch(sendcloud_class + '._cancel_shipment', new=_fake_cancel_shipment),
        ):
            delivery.button_validate()
        self.assertEqual(delivery.state, 'done')
