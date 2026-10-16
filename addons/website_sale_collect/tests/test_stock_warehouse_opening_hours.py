# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon


@tagged("post_install", "-at_install")
class TestStockWarehouseOpeningHours(ClickAndCollectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar = cls.env["resource.calendar"].create(
            {
                "name": "Test Opening Hours",
                "company_id": cls.warehouse.company_id.id,
                "attendance_ids": [
                    Command.create({"dayofweek": "0", "hour_from": 8, "hour_to": 12.5}),
                    Command.create({"dayofweek": "1", "hour_from": 0, "hour_to": 24}),
                ],
            }
        )
        cls.warehouse.opening_hours = cls.calendar

    def test_format_opening_hours_formats_periods_per_day(self):
        formatted_hours = self.warehouse._format_opening_hours(
            self.warehouse.opening_hours.attendance_ids
        )
        self.assertEqual(formatted_hours["0"], ["08:00 - 12:30"])
        self.assertEqual(formatted_hours["1"], ["00:00 - 24:00"])
        # Days without any attendance are empty
        for i in range(2, 7):
            self.assertEqual(formatted_hours[str(i)], [])
        self.assertEqual(len(formatted_hours.keys()), 7)

    def test_get_opening_hours_by_partner_batches_several_partners(self):
        other_warehouse = self.warehouse.sudo().copy(
            {"name": "Other Warehouse", "code": "OWH"}
        )
        other_warehouse.sudo().opening_hours = False
        partner_without_warehouse = self.env["res.partner"].create(
            {"name": "No Warehouse"}
        )

        opening_hours_by_partner = self.env[
            "stock.warehouse"
        ].get_opening_hours_by_partner(
            [
                self.warehouse.partner_id.id,
                other_warehouse.partner_id.id,
                partner_without_warehouse.id,
            ]
        )

        self.assertEqual(
            opening_hours_by_partner,
            {
                self.warehouse.partner_id.id: self.warehouse._format_opening_hours(
                    self.warehouse.opening_hours.attendance_ids
                ),
            },
        )

    def test_get_opening_hours_by_partner_uses_first_warehouse_of_shared_partner(self):
        """When several warehouses share a partner, the first one by sequence must be used."""
        other_calendar = self.env["resource.calendar"].sudo().create(
            {
                "name": "Other Opening Hours",
                "company_id": self.warehouse.company_id.id,
                "attendance_ids": [
                    Command.create({"dayofweek": "4", "hour_from": 14, "hour_to": 18}),
                ],
            }
        )
        other_warehouse = self.warehouse.sudo().copy(
            {"name": "Other Warehouse", "code": "OWH", "opening_hours": other_calendar.id}
        )
        self.warehouse.sudo().sequence = 10
        other_warehouse.sequence = 5
        self.assertEqual(other_warehouse.partner_id, self.warehouse.partner_id)

        opening_hours_by_partner = self.env[
            "stock.warehouse"
        ].get_opening_hours_by_partner([self.warehouse.partner_id.id])
        self.assertEqual(
            opening_hours_by_partner,
            {
                self.warehouse.partner_id.id: other_warehouse._format_opening_hours(
                    other_calendar.attendance_ids
                ),
            },
        )
