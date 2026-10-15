# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestStockWarehouse(ClickAndCollectCommon):
    _test_user_groups = (
        "base.group_user",
        "product.group_product_manager",
        "sales_team.group_sale_manager",  # FIXME: use sales_team.group_sale_salesman
    )

    _test_user_name = "Test Sales & Product Manager"

    def test_geolocation_geolocates_addresses_without_coordinates(self):
        self.warehouse.partner_id.write({"partner_latitude": 0.0, "partner_longitude": 0.0})
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize"
        ) as geo_localize_mock:
            self.warehouse._prepare_pickup_location_data()
            geo_localize_mock.assert_called_once()

    def test_geolocation_skips_invalid_addresses(self):
        self.warehouse.partner_id.write({
            "partner_latitude": 0.0,
            "partner_longitude": 0.0,
            "geo_localization_error": "No match found for address: 1 Fake Street",
        })
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize"
        ) as geo_localize_mock:
            self.warehouse._prepare_pickup_location_data()
            geo_localize_mock.assert_not_called()

    def test_geolocation_skips_addresses_with_coordinates(self):
        self.warehouse.partner_id.write({"partner_latitude": 1.0, "partner_longitude": 1.0})
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize"
        ) as geo_localize_mock:
            self.warehouse._prepare_pickup_location_data()
            geo_localize_mock.assert_not_called()
