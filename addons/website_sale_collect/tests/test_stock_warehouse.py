from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestStockWarehouse(ClickAndCollectCommon):
    _test_user_groups = None

    def test_geolocation_updates_unset_coordinates_of_valid_addresses(self):
        """Test that valid addresses with default coordinates are geolocated successfully."""
        self.warehouse.partner_id.write({
            "partner_latitude": 0.0,
            "partner_longitude": 0.0,
            "geo_localization_failed": False,
        })

        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize",
            return_value=(44.4323, 26.1063),
        ):
            self.warehouse.with_context(force_geo_localize=True)._prepare_pickup_location_data()

        self.assertEqual(self.warehouse.partner_id.partner_latitude, 44.4323)
        self.assertEqual(self.warehouse.partner_id.partner_longitude, 26.1063)
        self.assertEqual(self.warehouse.partner_id.geo_localization_failed, False)

    def test_geolocation_flags_invalid_addresses(self):
        """Test that invalid addresses are flagged after geolocation fails."""
        self.warehouse.partner_id.write({
            "partner_latitude": 0.0,
            "partner_longitude": 0.0,
            "geo_localization_failed": False,
        })

        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize",
            return_value=None,
        ):
            self.warehouse.with_context(force_geo_localize=True)._prepare_pickup_location_data()

        self.assertEqual(self.warehouse.partner_id.geo_localization_failed, True)

    def test_geolocation_skips_flagged_invalid_addresses(self):
        """Test that addresses flagged as invalid do not trigger additional geolocation requests."""
        self.warehouse.partner_id.write({
            "partner_latitude": 0.0,
            "partner_longitude": 0.0,
            "geo_localization_failed": True,
        })

        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize"
        ) as mock_geo_localize:
            self.warehouse.with_context(force_geo_localize=True)._prepare_pickup_location_data()
            mock_geo_localize.assert_not_called()

    def test_geolocation_skips_addresses_with_coordinates(self):
        """Test that addresses with valid non-zero coordinates are not geolocated."""
        test_coordinate_pairs = [
            (1.0, 1.0),  # Standard non-zero coordinates
            (0.0, 1.0),  # Equator alignment
            (1.0, 0.0),  # Prime Meridian alignment
        ]
        for lat, long in test_coordinate_pairs:
            self.warehouse.partner_id.write({
                "partner_latitude": lat,
                "partner_longitude": long,
                "geo_localization_failed": False,
            })
            with patch(
                "odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize"
            ) as mock_geo_localize:
                self.warehouse._prepare_pickup_location_data()
                mock_geo_localize.assert_not_called()
