from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestStockWarehouse(ClickAndCollectCommon):
    def test_geolocation_updates_unset_coordinates_of_valid_addresses(self):
        with patch(
            "odoo.addons.geocoding.models.res_partner.ResPartner.geo_localize",
            new=lambda self_: self_.write(
                {"partner_latitude": 1.0, "partner_longitude": 1.0}
            ),
        ):
            self.warehouse._update_missing_coordinates()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (1.0, 1.0))

    def test_geolocation_flags_coordinates_of_invalid_addresses(self):
        with patch(
            "odoo.addons.geocoding.models.res_partner.ResPartner.geo_localize",
            new=lambda self_: self_.write(
                {"partner_latitude": 0.0, "partner_longitude": 0.0}
            ),
        ):
            self.warehouse._update_missing_coordinates()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (1000.0, 1000.0))

    def test_geolocation_skips_addresses_with_coordinates(self):
        for lat, long in [
            (1.0, 1.0),
            (0.0, 1.0),
            (1.0, 0.0),
            (1000.0, 1000.0),
        ]:
            self.warehouse.partner_id.write(
                {"partner_latitude": lat, "partner_longitude": long}
            )
            with patch(
                "odoo.addons.geocoding.models.res_partner.ResPartner.geo_localize"
            ) as geo_localize_mock:
                self.warehouse._update_missing_coordinates()
                self.assertFalse(geo_localize_mock.called)
