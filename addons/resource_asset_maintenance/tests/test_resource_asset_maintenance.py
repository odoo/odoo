from datetime import UTC, datetime

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestResourceAssetMaintenance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.machinery = cls.env.ref("resource_asset.kind_machinery")
        cls.press = cls.env["resource.asset"].create(
            {"name": "Press 1", "kind_id": cls.machinery.id}
        )
        cls.team = cls.env["team.team"].create({"use_maintenance": True, "name": "Mechanics"})
        cls.stage_done = cls.env["maintenance.stage"].search(
            [("done", "=", True)], limit=1
        )
        cls.start = datetime(2026, 3, 2, 8, 0)
        cls.end = datetime(2026, 3, 2, 12, 0)

    def _request(self, **vals):
        return self.env["maintenance.request"].create(
            {
                "name": "Oil change",
                "asset_id": self.press.id,
                "maintenance_team_id": self.team.id,
                "schedule_date": self.start,
                "schedule_end": self.end,
                **vals,
            }
        )

    def _bookings(self):
        return self.env["resource.reservation"].search(
            [("resource_id", "=", self.press.resource_id.id)]
        )

    def test_a_request_in_progress_puts_the_asset_under_maintenance(self):
        new_stage, in_progress = self.env["maintenance.stage"].search([], limit=2)
        self.press.action_set_in_service()
        first = self._request(stage_id=new_stage.id, block_asset=False)
        self.assertEqual(self.press.state, "in_service")
        first.stage_id = in_progress
        self.assertEqual(self.press.state, "maintenance")
        second = self._request(name="Belt", stage_id=in_progress.id, block_asset=False)
        first.stage_id = self.stage_done
        self.assertEqual(self.press.state, "maintenance")
        second.archive = True
        self.assertEqual(self.press.state, "in_service")
        second.archive = False
        self.assertEqual(self.press.state, "maintenance")
        second.unlink()
        self.assertEqual(self.press.state, "in_service")

    def test_moving_a_request_to_another_asset_moves_the_maintenance(self):
        in_progress = self.env["maintenance.stage"].search([], limit=2)[1:]
        other = self.env["resource.asset"].create(
            {"name": "Press 2", "kind_id": self.machinery.id}
        )
        (self.press | other).action_set_in_service()
        request = self._request(stage_id=in_progress.id)
        self.assertEqual(self.press.state, "maintenance")
        request.asset_id = other
        self.assertEqual(self.press.state, "in_service")
        self.assertEqual(other.state, "maintenance")

    def test_requests_leave_an_asset_that_is_not_in_service_alone(self):
        in_progress = self.env["maintenance.stage"].search([], limit=2)[1:]
        self.assertEqual(self.press.state, "draft")
        request = self._request(stage_id=in_progress.id)
        self.assertEqual(self.press.state, "draft")
        self.press.action_set_out_of_service()
        request.stage_id = self.stage_done
        self.assertEqual(self.press.state, "out_of_service")

    def test_a_scheduled_request_blocks_the_asset(self):
        request = self._request()
        self.assertRecordValues(
            self._bookings(),
            [
                {
                    "res_model": "maintenance.request",
                    "res_id": request.id,
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
        request = self._request()
        request.write(
            {
                "schedule_date": datetime(2026, 3, 3, 8, 0),
                "schedule_end": datetime(2026, 3, 3, 9, 0),
            }
        )
        self.assertEqual(self._bookings().date_start, datetime(2026, 3, 3, 8, 0))
        request.block_asset = False
        self.assertFalse(self._bookings())
        request.block_asset = True
        self.assertEqual(len(self._bookings()), 1)

    def test_a_done_or_archived_request_releases_the_asset(self):
        request = self._request()
        request.stage_id = self.stage_done
        self.assertFalse(self._bookings())
        other = self._request(name="Belt")
        self.assertEqual(len(self._bookings()), 1)
        other.archive_equipment_request()
        self.assertFalse(self._bookings())

    def test_two_requests_cannot_block_the_same_window(self):
        from odoo.exceptions import ValidationError

        self._request()
        with self.assertRaises(ValidationError):
            self._request(
                name="Second",
                schedule_date=datetime(2026, 3, 2, 10, 0),
                schedule_end=datetime(2026, 3, 2, 14, 0),
            )

    def test_the_asset_counts_its_requests_and_lends_its_team(self):
        self.press.write({"maintenance_team_id": self.team.id})
        request = self.env["maintenance.request"].create({"name": "Check"})
        request.asset_id = self.press
        self.assertEqual(request.maintenance_team_id, self.team)
        self.press.invalidate_recordset()
        self.assertEqual(self.press.maintenance_count, 1)
        self.assertEqual(self.press.maintenance_open_count, 1)
        self.assertFalse(self._bookings(), "an unscheduled request blocks nothing")

    def test_the_asset_outranks_the_equipment_for_team_and_technician(self):
        """The bridge used to set the asset's team, then let the base compute
        overwrite it with the equipment's."""
        other_team = self.env["team.team"].create({"use_maintenance": True, "name": "Electricians"})
        technician = self.env["res.users"].create(
            {"name": "Asset tech", "login": "asset_tech"}
        )
        equipment = self.env["maintenance.equipment"].create(
            {"name": "Old press", "maintenance_team_id": other_team.id}
        )
        self.press.write(
            {"maintenance_team_id": self.team.id, "technician_user_id": technician.id}
        )
        request = self.env["maintenance.request"].create(
            {"name": "Check", "equipment_id": equipment.id, "asset_id": self.press.id}
        )
        self.assertEqual(request.maintenance_team_id, self.team)
        self.assertEqual(request.user_id, technician)
        request.asset_id = False
        self.assertEqual(request.maintenance_team_id, other_team)

    def test_an_asset_only_request_plans_an_activity_on_the_asset(self):
        request = self._request()
        activity = request.activity_ids.filtered(
            lambda a: (
                a.activity_type_id
                == self.env.ref("maintenance.mail_act_maintenance_request")
            )
        )
        self.assertEqual(len(activity), 1)
        self.assertIn(self.press.name, activity.note)

    def test_the_asset_outranks_the_work_centre(self):
        Request = self.env["maintenance.request"]
        if "workcenter_id" not in Request._fields:
            self.skipTest("mrp_maintenance is not installed")
        workcenter_team = self.env["team.team"].create({"use_maintenance": True, "name": "Line crew"})
        workcenter = self.env["mrp.workcenter"].create(
            {"name": "Press line", "maintenance_team_id": workcenter_team.id}
        )
        self.press.maintenance_team_id = self.team
        sources = {
            "maintenance_for": "workcenter",
            "workcenter_id": workcenter.id,
            "asset_id": self.press.id,
        }
        at_create = Request.create({"name": "Check", **sources})
        after_write = Request.create({"name": "Check", "maintenance_for": "workcenter"})
        after_write.write(sources)
        self.assertEqual(at_create.maintenance_team_id, self.team)
        self.assertEqual(after_write.maintenance_team_id, self.team)
