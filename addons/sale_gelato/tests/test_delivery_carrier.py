# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.delivery.tests.common import DeliveryCommon
from odoo.addons.sale_gelato.tests.common import GelatoCommon


@tagged('post_install', '-at_install')
class TestDeliveryCarrier(GelatoCommon, DeliveryCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner.write({
            'street': 'Street',
            'city': 'City',
            'zip': '3001',
            'country_id': cls.env.ref("base.be").id,
        })

        cls.product_delivery_gelato = cls._prepare_carrier_product(name='Gelato Charges')
        cls.gelato_delivery = cls._prepare_carrier(
            cls.product_delivery_gelato, delivery_type='gelato'
        )

        cls.shipping_response = {
            "quotes": [
                {
                    "shipmentMethods": [
                        {"price": 5, "type": "normal"},
                        {"price": 9, "type": "normal"},
                        {"price": 20, "type": "express"},
                        {"price": 30, "type": "express"},
                    ]
                }
            ]
        }

    def test_gelato_delivery_is_not_available_for_generic_order(self):
        self.assertFalse(self.gelato_delivery._is_available_for_order(self.sale_order))

    def test_generic_delivery_is_not_available_for_gelato_order(self):
        self.assertFalse(self.free_delivery._is_available_for_order(self.gelato_order))

    def test_only_generic_carriers_are_available_for_generic_order(self):
        all_carriers = self.env['delivery.carrier'].search([])
        standard_carriers = all_carriers.available_carriers(self.partner, self.sale_order)
        self.assertFalse(
            standard_carriers.filtered(lambda carrier: carrier.delivery_type == 'gelato')
        )

    def test_only_gelato_carriers_are_available_for_gelato_order(self):
        all_carriers = self.env['delivery.carrier'].search([])
        gelato_carriers = all_carriers.available_carriers(self.partner, self.gelato_order)
        self.assertFalse(
            gelato_carriers.filtered(lambda carrier: carrier.delivery_type != 'gelato')
        )

    def test_incomplete_partner_address_prevents_delivery(self):
        self.gelato_order.partner_id.street = ''
        self.assertIsNotNone(
            self.gelato_delivery._ensure_partner_address_is_complete(self.gelato_order.partner_id)
        )

    def test_get_cheapest_normal_delivery_price(self):
        with patch(
            'odoo.addons.sale_gelato.utils.make_request', return_value=self.shipping_response
        ):
            delivery_price = self.gelato_delivery.gelato_rate_shipment(self.gelato_order)
            self.assertEqual(delivery_price['price'], 5)

    def test_get_cheapest_express_delivery_price(self):
        self.gelato_delivery.gelato_shipping_service_type = 'express'
        with patch(
            'odoo.addons.sale_gelato.utils.make_request', return_value=self.shipping_response
        ):
            delivery_price = self.gelato_delivery.gelato_rate_shipment(self.gelato_order)
            self.assertEqual(delivery_price['price'], 20)
