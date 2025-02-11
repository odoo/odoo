# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestDeliveryCarrier(ClickAndCollectCommon, WebsiteSaleStockCommon):

    def test_prevent_publishing_when_no_warehouse(self):
        self.in_store_dm.is_published = False
        self.in_store_dm.warehouse_ids = [Command.clear()]
        with self.assertRaises(ValidationError):
            self.in_store_dm.is_published = True

    def test_same_company_for_delivery_method_and_warehouse(self):
        self.in_store_dm.company_id = self.company_id
        self.companyA = self.env['res.company'].create({'name': 'Company A'})
        self.warehouse_2 = self._create_warehouse(company_id=self.companyA.id)
        with self.assertRaises(ValidationError):
            self.in_store_dm.warehouse_ids = [Command.set([self.warehouse_2.id])]

    def test_creating_in_store_delivery_method_sets_integration_level_to_rate(self):
        new_in_store_carrier = self.env['delivery.carrier'].create({
            'name': "Test Carrier",
            'delivery_type': 'in_store',
            'product_id': self.dm_product.id,
        })
        self.assertEqual(new_in_store_carrier.integration_level, 'rate')

    def test_in_store_get_close_locations_returned_data(self):
        so = self._create_in_store_delivery_order()
        # Create a partner for a warehouse.
        wh_address_partner = self.env['res.partner'].create({
            **self.dummy_partner_address_values,
            'name': "Shop 1",
            'partner_latitude': 1.0,
            'partner_longitude': 2.0,
        })
        self.warehouse.partner_id = wh_address_partner.id
        self.warehouse.opening_hours = self.env['resource.calendar'].create({
            'name': 'Opening hours',
            'attendance_ids': [
                Command.create({
                    'name': 'Monday Morning',
                    'dayofweek': '0',
                    'hour_from': 8,
                    'hour_to': 12,
                    'day_period': 'morning',
                }),
                Command.create({
                    'name': 'Monday Lunch',
                    'dayofweek': '0',
                    'hour_from': 12,
                    'hour_to': 13,
                    'day_period': 'lunch',
                }),
                Command.create({
                    'name': 'Monday Afternoon',
                    'dayofweek': '0',
                    'hour_from': 13,
                    'hour_to': 17,
                    'day_period': 'afternoon',
                }),
            ],
        })

        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize',
            return_value=True
        ), MockRequest(self.env, website=self.website, sale_order_id=so.id):
            locations = self.in_store_dm._in_store_get_close_locations(wh_address_partner)
            self.assertEqual(
                locations, [{
                    'id': self.warehouse.id,
                    'name': wh_address_partner['name'].title(),
                    'street': wh_address_partner['street'].title(),
                    'city': wh_address_partner.city.title(),
                    'zip_code': wh_address_partner.zip,
                    'country_code': wh_address_partner.country_code,
                    'latitude': wh_address_partner.partner_latitude,
                    'longitude': wh_address_partner.partner_longitude,
                    'additional_data': {'in_store_stock': {'in_stock': True}},
                    'opening_hours': {
                        '0': ['08:00 - 12:00', '13:00 - 17:00'],
                        '1': [],
                        '2': [],
                        '3': [],
                        '4': [],
                        '5': [],
                        '6': [],
                    },
                    'distance': 0.0,
                }]
            )
