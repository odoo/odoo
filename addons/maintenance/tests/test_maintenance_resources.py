from datetime import UTC, datetime

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMaintenanceResources(TransactionCase):
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
                "resource_ids": [(6, 0, self.press.resource_id.ids)],
                "maintenance_team_id": self.team.id,
                "date_scheduled_start": self.start,
                "date_scheduled_end": self.end,
                "block_resource": True,
                "state": "confirmed",
                **vals,
            }
        )

    def _bookings(self, asset=None):
        return self.env["resource.reservation"].search(
            [("resource_id", "=", (asset or self.press).resource_id.id)]
        )

    def test_an_order_in_progress_puts_the_asset_under_maintenance(self):
        self.press.action_set_in_service()
        first = self._order(block_resource=False)
        self.assertEqual(self.press.state, "in_service")
        first.action_start()
        self.assertEqual(self.press.state, "maintenance")
        second = self._order(name="Belt", state="in_progress", block_resource=False)
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
        order.resource_ids = other.resource_id
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
                "date_scheduled_start": datetime(2026, 3, 3, 8, 0),
                "date_scheduled_end": datetime(2026, 3, 3, 9, 0),
            }
        )
        self.assertEqual(self._bookings().date_start, datetime(2026, 3, 3, 8, 0))
        order.block_resource = False
        self.assertFalse(self._bookings())
        order.block_resource = True
        self.assertEqual(len(self._bookings()), 1)

    def test_a_done_order_keeps_its_window_and_a_cancelled_one_releases_it(self):
        order = self._order()
        order.action_done()
        self.assertEqual(len(self._bookings()), 1)
        order.sudo().reservation_ids.unlink()
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
        self._order()
        with self.assertRaises(UserError):
            self._order(
                name="Second",
                date_scheduled_start=datetime(2026, 3, 2, 10, 0),
                date_scheduled_end=datetime(2026, 3, 2, 14, 0),
            )

    def test_the_asset_counts_its_orders_and_lends_its_team(self):
        self.press.write({"maintenance_team_id": self.team.id})
        order = self.env["maintenance.order"].create({"name": "Check"})
        order.resource_ids = self.press.resource_id
        self.assertEqual(order.maintenance_team_id, self.team)
        self.press.invalidate_recordset()
        self.assertEqual(self.press.maintenance_count, 1)
        self.assertEqual(self.press.maintenance_open_count, 1)
        self.assertFalse(self._bookings(), "an unscheduled order blocks nothing")

    def test_the_kind_stands_in_for_an_asset_without_team_or_technician(self):
        electricians = self.env["team.team"].create(
            {"use_maintenance": True, "name": "Electricians"}
        )
        technician = self.env["res.users"].create(
            {"name": "Kind tech", "login": "kind_tech"}
        )
        kind = self.env["resource.asset.kind"].create(
            {
                "name": "Panels",
                "code": "panels_probe",
                "maintenance_team_id": electricians.id,
                "technician_user_id": technician.id,
            }
        )
        panel = self.env["resource.asset"].create({"name": "Panel", "kind_id": kind.id})
        self.assertEqual(panel.maintenance_team_id, electricians)
        panel.resource_id.write(
            {"maintenance_team_id": False, "technician_user_id": False}
        )
        order = self.env["maintenance.order"].create(
            {"name": "Check", "resource_ids": [(6, 0, panel.resource_id.ids)]}
        )
        self.assertEqual(order.maintenance_team_id, electricians)
        self.assertEqual(order.user_id, technician)

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

    def test_a_typed_in_order_is_refused_a_window_a_work_order_holds(self):
        self.env["resource.reservation"].create(
            {
                "name": "Production run",
                "resource_id": self.press.resource_id.id,
                "date_start": datetime(2026, 3, 2, 11, 0),
                "date_end": datetime(2026, 3, 2, 13, 0),
                "enforcement_mode": "soft",
            }
        )
        with self.assertRaises(UserError):
            self._order()

    def test_a_plan_occurrence_moves_past_what_holds_its_window(self):
        self.env["resource.reservation"].create(
            {
                "name": "Production run",
                "resource_id": self.press.resource_id.id,
                "date_start": datetime(2026, 3, 2, 7, 0),
                "date_end": datetime(2026, 3, 2, 10, 0),
                "enforcement_mode": "soft",
            }
        )
        plan = self.env["maintenance.plan"].create(
            {
                "name": "Monthly",
                "resource_ids": [(6, 0, self.press.resource_id.ids)],
                "block_resource": True,
                "repeat_anchor": "fixed",
                "repeat_interval": 1,
                "repeat_unit": "month",
                "tz": "UTC",
                "date_first_occurrence": datetime(2026, 3, 2, 8, 0),
                "duration": 2,
            }
        )
        order = plan.order_ids
        self.assertEqual(order.date_scheduled_start, datetime(2026, 3, 2, 10, 0))
        self.assertEqual(
            order.reservation_ids.mapped("date_start"), [datetime(2026, 3, 2, 10, 0)]
        )

    def test_one_order_books_every_resource_it_names(self):
        tractor = self.env["resource.asset"].create(
            {"name": "Tractor", "kind_id": self.machinery.id}
        )
        order = self._order(
            resource_ids=[(6, 0, (self.press | tractor).resource_id.ids)]
        )
        self.assertEqual(order.asset_ids, self.press | tractor)
        self.assertEqual(len(self._bookings()), 1)
        self.assertEqual(len(self._bookings(tractor)), 1)

    def test_maintaining_a_component_books_what_it_is_part_of(self):
        line = self.env["resource.asset"].create(
            {"name": "Press line", "kind_id": self.machinery.id}
        )
        self.press.parent_id = line
        self._order()
        self.assertEqual(len(self._bookings()), 1)
        self.assertEqual(len(self._bookings(line)), 1)

    def test_a_fixed_plan_books_its_next_occurrences_ahead(self):
        plan = self.env["maintenance.plan"].create(
            {
                "name": "Weekly",
                "resource_ids": [(6, 0, self.press.resource_id.ids)],
                "block_resource": True,
                "repeat_anchor": "fixed",
                "repeat_interval": 1,
                "repeat_unit": "week",
                "tz": "UTC",
                "date_first_occurrence": datetime(2026, 3, 2, 8, 0),
                "book_ahead_count": 2,
            }
        )
        self.assertEqual(
            sorted(plan.order_ids.reservation_ids.mapped("date_start")),
            [
                datetime(2026, 3, 2, 8, 0),
                datetime(2026, 3, 9, 8, 0),
                datetime(2026, 3, 16, 8, 0),
            ],
        )
        plan.order_ids.action_done()
        done = plan.order_ids.filtered(lambda o: o.state == "done")
        self.assertEqual(
            done.reservation_ids.mapped("date_start"), [datetime(2026, 3, 2, 8, 0)]
        )

    def test_a_machine_that_is_both_asset_and_resource_reports_one_mtbf(self):
        self.press.expected_mtbf = 30
        self.assertEqual(self.press.resource_id.expected_mtbf, 30)
        self._order(maintenance_type="corrective", state="done")
        self.press.invalidate_recordset()
        self.assertEqual(self.press.maintenance_count, 1)
        self.assertEqual(
            self.press.maintenance_count, self.press.resource_id.maintenance_count
        )
