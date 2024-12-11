# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_collect.tests.common import InStoreCommon
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestDeliveryCarrier(InStoreCommon, WebsiteSaleStockCommon):

    def test_if_no_wh_raise_error_when_publish(self):
        self.in_store_dm.is_published = False
        self.in_store_dm.warehouse_ids = False
        with self.assertRaises(ValidationError):
            self.in_store_dm.is_published = True

    def test_onchange_carrier_to_in_store_unpublishes_dm(self):
        with Form(self.free_delivery) as delivery_form:
            delivery_form.delivery_type = 'in_store'
        self.assertFalse(self.free_delivery.is_published)

    def test_onchange_carrier_to_in_store_sets_integration_level_to_rate(self):
        with Form(self.free_delivery) as delivery_form:
            delivery_form.delivery_type = 'in_store'
        self.assertEqual(self.free_delivery.integration_level, 'rate')

    def test_create_in_store_carrier_sets_integration_level_to_rate(self):
        new_in_store_carrier = self.env['delivery.carrier'].create({
            'name': "Test Carrier",
            'delivery_type': 'in_store',
            'product_id': self.dm_product.id,
        })
        self.assertEqual(new_in_store_carrier.integration_level, 'rate')

    def test_in_store_get_close_locations_return_format(self):
        so = self._create_so_in_store_dm()
        # Create a partner for a warehouse.
        wh_address_partner = self.env['res.partner'].create({
            **self.dummy_partner_address_values,
            'name': "Shop 1",
            'partner_latitude': 1.0,
            'partner_longitude': 2.0,
        })
        self.warehouse.partner_id = wh_address_partner.id

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
                    'opening_hours': {},
                    'distance': 0.0,
                }]
            )
