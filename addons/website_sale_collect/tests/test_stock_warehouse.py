# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestStockWarehouse(ClickAndCollectCommon):
    _test_user_groups = (
        'base.group_user',
        'product.group_product_manager',
        'sales_team.group_sale_manager',  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = 'Test Sales & Product Manager'

    def test_geolocation_updates_unset_coordinates_of_valid_addresses(self):
        """Test that valid addresses with default coordinates are geolocated."""
        self.warehouse.partner_id.write({"partner_latitude": 0.0, "partner_longitude": 0.0})
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize",
            return_value=(44.4323, 26.1063),
        ):
            self.warehouse.with_context(force_geo_localize=True)._prepare_pickup_location_data()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (44.4323, 26.1063))

    def test_geolocation_is_attempted_only_once_for_invalid_addresses(self):
        """Test that a warehouse whose address cannot be geolocated is not geolocated again.

        This prevents a spam of OpenStreetMap's API when warehouses with an invalid address are
        loaded in the location selector of Click and Collect.
        """
        self.warehouse.partner_id.write({"partner_latitude": 0.0, "partner_longitude": 0.0})
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize",
            return_value=None,
        ) as geo_localize_mock:
            warehouse = self.warehouse.with_context(force_geo_localize=True)
            warehouse._prepare_pickup_location_data()
            warehouse._prepare_pickup_location_data()
            self.assertEqual(geo_localize_mock.call_count, 1)

    def test_geolocation_skips_addresses_with_coordinates(self):
        """Test that addresses with coordinates are not geolocated."""
        for lat, long in [
            (1.0, 1.0),  # Valid random coordinates.
            (0.0, 1.0),  # Valid coordinates aligned on the Equator.
            (1.0, 0.0),  # Valid coordinates aligned on the Prime Meridian.
        ]:
            self.warehouse.partner_id.write({"partner_latitude": lat, "partner_longitude": long})
            with patch(
                "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize"
            ) as geo_localize_mock:
                self.warehouse.with_context(force_geo_localize=True)._prepare_pickup_location_data()
                self.assertFalse(geo_localize_mock.called)
