# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Command
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
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize",
            new=lambda self_: self_.write({"partner_latitude": 1.0, "partner_longitude": 1.0}),
        ):
            self.warehouse._prepare_pickup_location_data()
        latitude = self.warehouse.partner_id.partner_latitude
        longitude = self.warehouse.partner_id.partner_longitude
        self.assertEqual((latitude, longitude), (1.0, 1.0))

    def test_geolocation_flags_coordinates_of_invalid_addresses(self):
        """Test that invalid addresses with default coordinates are assigned invalid coordinates."""
        with patch(
            "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize",
            new=lambda self_: self_.write({"partner_latitude": 0.0, "partner_longitude": 0.0}),
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
            self.warehouse.partner_id.write({"partner_latitude": lat, "partner_longitude": long})
            with patch(
                "odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize"
            ) as geo_localize_mock:
                self.warehouse._prepare_pickup_location_data()
                self.assertFalse(geo_localize_mock.called)


@tagged('post_install', '-at_install')
class TestStockWarehouseOpeningHours(ClickAndCollectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env['resource.calendar'].create({
            'name': "Test Opening Hours",
            'company_id': cls.warehouse.company_id.id,
            'attendance_ids': [
                Command.create({'dayofweek': '0', 'hour_from': 8, 'hour_to': 12.5}),
                Command.create({'dayofweek': '1', 'hour_from': 0, 'hour_to': 24}),
            ],
        })
        cls.warehouse.opening_hours = cls.calendar

    def test_format_opening_hours_formats_periods_per_day(self):
        formatted_hours = self.warehouse._format_opening_hours(
            self.warehouse.opening_hours.attendance_ids
        )
        self.assertEqual(formatted_hours['0'], ["08:00 - 12:30"])
        self.assertEqual(formatted_hours['1'], ["00:00 - 24:00"])
        # Days without any attendance are empty
        for i in range(2, 7):
            self.assertEqual(formatted_hours[str(i)], [])
        self.assertEqual(len(formatted_hours.keys()), 7)

    def test_get_opening_hours_by_partner_batches_several_partners(self):
        other_warehouse = self.warehouse.sudo().copy({'name': "Other Warehouse", 'code': "OWH"})
        other_warehouse.sudo().opening_hours = False
        partner_without_warehouse = self.env['res.partner'].create({'name': "No Warehouse"})

        opening_hours_by_partner = self.env['stock.warehouse'].get_opening_hours_by_partner([
            self.warehouse.partner_id.id,
            other_warehouse.partner_id.id,
            partner_without_warehouse.id,
        ])

        self.assertEqual(
            opening_hours_by_partner, {
                self.warehouse.partner_id.id: self.warehouse._format_opening_hours(
                    self.warehouse.opening_hours.attendance_ids
                ),
            }
        )
