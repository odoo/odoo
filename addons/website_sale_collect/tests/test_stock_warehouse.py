# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged('post_install', '-at_install')
class TestStockWarehouse(ClickAndCollectCommon):
    def test_geolocation_updates_unset_coordinates_of_valid_addresses(self):
        """Test that valid addresses with default coordinates are geolocated."""
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize',
            new=lambda self_: self_.write({'partner_latitude': 1.0, 'partner_longitude': 1.0}),
        ):
            self.warehouse._prepare_pickup_location_data()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (1.0, 1.0))

    def test_geolocation_flags_coordinates_of_invalid_addresses(self):
        """Test that invalid addresses with default coordinates are assigned invalid coordinates."""
        with patch(
            'odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize',
            new=lambda self_: self_.write({'partner_latitude': 0.0, 'partner_longitude': 0.0}),
        ):
            self.warehouse._prepare_pickup_location_data()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (1000.0, 1000.0))  # Invalid coordinates.

    def test_geolocation_skips_addresses_with_coordinates(self):
        """Test that addresses with either valid or invalid coordinates are not geolocated."""
        for lat, long in [
            (1.0, 1.0),  # Valid random coordinates.
            (0.0, 1.0),  # Valid coordinates aligned on the Equator.
            (1.0, 0.0),  # Valid coordinates aligned on the Prime Meridian.
            (1000.0, 1000.0),  # Invalid (!) coordinates.
        ]:
            self.warehouse.partner_id.write({'partner_latitude': lat, 'partner_longitude': long})
            with patch(
                'odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize'
            ) as geo_localize_mock:
                self.warehouse._prepare_pickup_location_data()
                self.assertFalse(geo_localize_mock.called)
