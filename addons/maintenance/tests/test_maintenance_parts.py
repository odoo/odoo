from datetime import datetime

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceParts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["approval.category"].search(
            [
                (
                    "approval_type",
                    "in",
                    ("maintenance_preventive", "maintenance_corrective"),
                )
            ]
        ).action_archive()
        cls.kind = cls.env["resource.asset.kind"].create(
            {"name": "Maintained Truck", "code": "maintained_truck"}
        )
        cls.pump_position = cls.env["resource.asset.kind.position"].create(
            {
                "kind_id": cls.kind.id,
                "name": "Fuel pump",
                "code": "fuel_pump",
                "expected_life_days": 365,
            }
        )
        cls.pump = cls.env["product.product"].create({"name": "Fuel pump"})
        cls.truck = cls.env["resource.asset"].create(
            {"name": "Truck 12", "kind_id": cls.kind.id}
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Diesel Workshop"})
        cls.team = cls.env["team.team"].create(
            {"use_maintenance": True, "name": "Fleet"}
        )

    def _order(self, **vals):
        return self.env["maintenance.order"].create(
            {
                "name": "Fuel pump failure",
                "resource_ids": [(6, 0, self.truck.resource_id.ids)],
                "maintenance_team_id": self.team.id,
                "block_resource": False,
                **vals,
            }
        )

    def _part(self, order, **vals):
        return self.env["resource.asset.part"].create(
            {
                "maintenance_order_id": order.id,
                "asset_id": self.truck.id,
                "position_id": self.pump_position.id,
                "product_id": self.pump.id,
                **vals,
            }
        )

    def _finish(self, order):
        order.action_confirm()
        order.action_done()

    def test_closing_an_order_installs_its_parts_as_the_vendors(self):
        order = self._order(vendor_id=self.vendor.id)
        part = self._part(order, serial="FP-1", removed_returned=True)

        self._finish(order)

        self.assertEqual(part.state, "installed")
        self.assertEqual(part.vendor_id, self.vendor)
        self.assertEqual(part.source, "maintenance")
        self.assertEqual(part.review_state, "none")

    def test_an_in_house_order_credits_its_technician(self):
        order = self._order(user_id=self.env.user.id)
        part = self._part(order)

        self._finish(order)

        self.assertFalse(part.vendor_id)
        self.assertEqual(part.user_id, self.env.user)
        self.assertEqual(part.review_state, "none")

    def test_the_same_position_twice_in_one_order_is_flagged(self):
        order = self._order(vendor_id=self.vendor.id)
        first = self._part(order, removed_returned=True)
        second = self._part(order, removed_returned=True)

        self._finish(order)

        self.assertEqual(second.previous_part_id, first)
        self.assertEqual(
            set(second.flag_ids.mapped("reason")), {"same_work", "within_life"}
        )
        self.assertEqual(order.part_flagged_count, 1)

    def test_a_vendor_part_not_returned_at_closing_is_flagged(self):
        order = self._order(vendor_id=self.vendor.id)
        part = self._part(order)

        self._finish(order)

        self.assertEqual(part.flag_ids.reason, "not_returned")
        part.removed_returned = True
        self.assertEqual(part.review_state, "cleared")

    def test_a_repeat_across_orders_is_flagged_on_the_later_one(self):
        earlier = self._order(vendor_id=self.vendor.id)
        self._part(earlier, removed_returned=True, date_installed=datetime(2026, 1, 5))
        self._finish(earlier)
        later = self._order(vendor_id=self.vendor.id)
        repeat = self._part(
            later, removed_returned=True, date_installed=datetime(2026, 3, 5)
        )

        self._finish(later)

        self.assertEqual(repeat.flag_ids.reason, "within_life")

    def test_cancelling_an_order_cancels_its_planned_parts_and_back(self):
        order = self._order()
        part = self._part(order)
        order.action_confirm()

        order.action_cancel()
        self.assertEqual(part.state, "cancelled")

        order.action_draft()
        self.assertEqual(part.state, "draft")

    def test_a_done_orders_parts_do_not_change(self):
        order = self._order(vendor_id=self.vendor.id)
        part = self._part(order, serial="FP-1", removed_returned=True)
        self._finish(order)

        with self.assertRaises(UserError):
            part.serial = "FP-2"
