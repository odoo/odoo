from datetime import UTC, datetime

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetMaintenance(TransactionCase):
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
        cls.machinery = cls.env.ref("resource_asset.kind_machinery")
        cls.press = cls.env["resource.asset"].create(
            {"name": "Press 1", "kind_id": cls.machinery.id}
        )
        cls.team = cls.env["team.team"].create(
            {"use_maintenance": True, "name": "Mechanics"}
        )
        cls.start = datetime(2026, 3, 2, 8, 0)
        cls.end = datetime(2026, 3, 2, 12, 0)

    def _order(self, **vals):
        return self.env["maintenance.order"].create(
            {
                "name": "Oil change",
                "asset_id": self.press.id,
                "maintenance_team_id": self.team.id,
                "schedule_date": self.start,
                "schedule_end": self.end,
                "block_asset": True,
                "state": "confirmed",
                **vals,
            }
        )

    def _bookings(self):
        return self.env["resource.reservation"].search(
            [("resource_id", "=", self.press.resource_id.id)]
        )

    def test_an_order_in_progress_puts_the_asset_under_maintenance(self):
        self.press.action_set_in_service()
        first = self._order(block_asset=False)
        self.assertEqual(self.press.state, "in_service")
        first.action_start()
        self.assertEqual(self.press.state, "maintenance")
        second = self._order(name="Belt", state="in_progress", block_asset=False)
        first.action_done()
        self.assertEqual(self.press.state, "maintenance")
        second.action_cancel()
        self.assertEqual(self.press.state, "in_service")
        second.action_draft()
        second.unlink()
        self.assertEqual(self.press.state, "in_service")

    def test_moving_an_order_to_another_asset_moves_the_maintenance(self):
        other = self.env["resource.asset"].create(
            {"name": "Press 2", "kind_id": self.machinery.id}
        )
        (self.press | other).action_set_in_service()
        order = self._order(state="in_progress")
        self.assertEqual(self.press.state, "maintenance")
        order.asset_id = other
        self.assertEqual(self.press.state, "in_service")
        self.assertEqual(other.state, "maintenance")

    def test_orders_leave_an_asset_that_is_not_in_service_alone(self):
        self.assertEqual(self.press.state, "draft")
        order = self._order(state="in_progress")
        self.assertEqual(self.press.state, "draft")
        self.press.action_set_out_of_service()
        order.action_done()
        self.assertEqual(self.press.state, "out_of_service")

    def test_a_scheduled_order_blocks_the_asset(self):
        order = self._order()
        self.assertRecordValues(
            self._bookings(),
            [
                {
                    "res_model": "maintenance.order",
                    "res_id": order.id,
                    "date_start": self.start,
                    "date_end": self.end,
                    "enforcement_mode": "hard",
                }
            ],
        )
        unavailable = self.press.resource_id._get_unavailable_intervals(
            datetime(2026, 3, 2, tzinfo=UTC), datetime(2026, 3, 3, tzinfo=UTC)
        )[self.press.resource_id.id]
        self.assertTrue(
            any(
                s <= self.start.replace(tzinfo=UTC)
                and e >= self.end.replace(tzinfo=UTC)
                for s, e in unavailable
            )
        )

    def test_the_block_follows_the_schedule_and_the_flag(self):
        order = self._order()
        order.write(
            {
                "schedule_date": datetime(2026, 3, 3, 8, 0),
                "schedule_end": datetime(2026, 3, 3, 9, 0),
            }
        )
        self.assertEqual(self._bookings().date_start, datetime(2026, 3, 3, 8, 0))
        order.block_asset = False
        self.assertFalse(self._bookings())
        order.block_asset = True
        self.assertEqual(len(self._bookings()), 1)

    def test_a_done_or_cancelled_order_releases_the_asset(self):
        order = self._order()
        order.action_done()
        self.assertFalse(self._bookings())
        other = self._order(name="Belt")
        self.assertEqual(len(self._bookings()), 1)
        other.action_cancel()
        self.assertFalse(self._bookings())

    def test_a_draft_order_does_not_block_the_asset_until_confirmed(self):
        order = self._order(state="draft")
        self.assertFalse(self._bookings())
        order.action_confirm()
        self.assertEqual(len(self._bookings()), 1)

    def test_two_orders_cannot_block_the_same_window(self):
        from odoo.exceptions import ValidationError

        self._order()
        with self.assertRaises(ValidationError):
            self._order(
                name="Second",
                schedule_date=datetime(2026, 3, 2, 10, 0),
                schedule_end=datetime(2026, 3, 2, 14, 0),
            )

    def test_the_asset_counts_its_orders_and_lends_its_team(self):
        self.press.write({"maintenance_team_id": self.team.id})
        order = self.env["maintenance.order"].create({"name": "Check"})
        order.asset_id = self.press
        self.assertEqual(order.maintenance_team_id, self.team)
        self.press.invalidate_recordset()
        self.assertEqual(self.press.maintenance_count, 1)
        self.assertEqual(self.press.maintenance_open_count, 1)
        self.assertFalse(self._bookings(), "an unscheduled order blocks nothing")

    def test_the_asset_outranks_the_equipment_for_team_and_technician(self):
        """The bridge used to set the asset's team, then let the base compute
        overwrite it with the equipment's."""
        other_team = self.env["team.team"].create(
            {"use_maintenance": True, "name": "Electricians"}
        )
        technician = self.env["res.users"].create(
            {"name": "Asset tech", "login": "asset_tech"}
        )
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Old press", "maintenance_team_id": other_team.id}
        )
        self.press.write(
            {"maintenance_team_id": self.team.id, "technician_user_id": technician.id}
        )
        order = self.env["maintenance.order"].create(
            {"name": "Check", "equipment_id": equipment.id, "asset_id": self.press.id}
        )
        self.assertEqual(order.maintenance_team_id, self.team)
        self.assertEqual(order.user_id, technician)
        order.asset_id = False
        self.assertEqual(order.maintenance_team_id, other_team)

    def test_an_asset_only_order_plans_an_activity_on_the_asset(self):
        order = self._order()
        activity = order.activity_ids.filtered(
            lambda a: (
                a.activity_type_id
                == self.env.ref("maintenance.mail_act_maintenance_order")
            )
        )
        self.assertEqual(len(activity), 1)
        self.assertIn(self.press.name, activity.note)

    def test_the_asset_outranks_the_work_centre(self):
        Order = self.env["maintenance.order"]
        if "workcenter_id" not in Order._fields:
            self.skipTest("mrp_maintenance is not installed")
        workcenter_team = self.env["team.team"].create(
            {"use_maintenance": True, "name": "Line crew"}
        )
        workcenter = self.env["mrp.workcenter"].create(
            {"name": "Press line", "maintenance_team_id": workcenter_team.id}
        )
        self.press.maintenance_team_id = self.team
        sources = {
            "maintenance_for": "workcenter",
            "workcenter_id": workcenter.id,
            "asset_id": self.press.id,
        }
        at_create = Order.create({"name": "Check", **sources})
        after_write = Order.create({"name": "Check", "maintenance_for": "workcenter"})
        after_write.write(sources)
        self.assertEqual(at_create.maintenance_team_id, self.team)
        self.assertEqual(after_write.maintenance_team_id, self.team)
