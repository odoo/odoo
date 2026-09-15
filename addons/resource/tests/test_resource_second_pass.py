from datetime import UTC, datetime

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.libs.datetime import timezone
from odoo.tests.common import TransactionCase


class TestResourceSecondPass(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["res.company"].create({"name": "Second Pass Co"})
        cls.calendar = cls.env["resource.calendar"].create(
            {"name": "SP calendar", "company_id": cls.company.id, "tz": "UTC"}
        )

    def _resource(self, **vals):
        return self.env["resource.resource"].create(
            {
                "name": vals.pop("name", "SP resource"),
                "company_id": vals.pop("company_id", self.company.id),
                "calendar_id": vals.pop("calendar_id", self.calendar.id),
                "tz": vals.pop("tz", "UTC"),
                **vals,
            }
        )

    def test_single_zero_length_attendance_is_not_an_overlap(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "zero",
                "company_id": self.company.id,
                "tz": "UTC",
                "attendance_ids": [Command.clear()],
            }
        )
        calendar.attendance_ids = [
            Command.create(
                {
                    "name": "zero length",
                    "dayofweek": "0",
                    "hour_from": 9.0,
                    "hour_to": 9.0,
                    "day_period": "morning",
                }
            )
        ]
        calendar.flush_recordset()
        self.assertEqual(len(calendar.attendance_ids), 1)

    def test_duration_based_zero_day_does_not_brick_the_calendar(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "duration", "company_id": self.company.id, "tz": "UTC"}
        )
        calendar.switch_based_on_duration()
        calendar.flush_recordset()

        attendance = calendar.attendance_ids.filtered(lambda a: not a.display_type)[0]
        attendance.duration_hours = 0.0
        calendar.flush_recordset()
        self.assertEqual(attendance.hour_from, attendance.hour_to)

        calendar.attendance_ids = [
            Command.create(
                {
                    "name": "Saturday",
                    "dayofweek": "5",
                    "hour_from": 9.0,
                    "hour_to": 11.0,
                    "day_period": "morning",
                }
            )
        ]
        calendar.flush_recordset()

    def test_real_overlap_is_still_rejected(self):
        calendar = self.env["resource.calendar"].create(
            {
                "name": "overlapping",
                "company_id": self.company.id,
                "tz": "UTC",
                "attendance_ids": [Command.clear()],
            }
        )
        with self.assertRaises(ValidationError):
            calendar.attendance_ids = [
                Command.create(
                    {
                        "name": "a",
                        "dayofweek": "0",
                        "hour_from": 8.0,
                        "hour_to": 12.0,
                        "day_period": "morning",
                    }
                ),
                Command.create(
                    {
                        "name": "b",
                        "dayofweek": "0",
                        "hour_from": 11.0,
                        "hour_to": 15.0,
                        "day_period": "afternoon",
                    }
                ),
            ]
            calendar.flush_recordset()

    def test_section_without_week_type_is_rejected(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "2w", "company_id": self.company.id, "tz": "UTC"}
        )
        calendar.switch_calendar_type()
        calendar.flush_recordset()
        with self.assertRaises(ValidationError):
            self.env["resource.calendar.attendance"].create(
                {
                    "name": "Orphan section",
                    "calendar_id": calendar.id,
                    "dayofweek": "0",
                    "hour_from": 0,
                    "hour_to": 0,
                    "day_period": "morning",
                    "display_type": "line_section",
                }
            )

    def test_legacy_section_without_week_type_still_reads(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "2w legacy", "company_id": self.company.id, "tz": "UTC"}
        )
        calendar.switch_calendar_type()
        calendar.flush_recordset()
        section = calendar.attendance_ids.filtered(
            lambda a: a.display_type == "line_section"
        )[0]
        self.env.cr.execute(
            "UPDATE resource_calendar_attendance SET week_type = NULL WHERE id = %s",
            (section.id,),
        )
        section.invalidate_recordset()
        self.assertTrue(section.display_name)

    def test_fully_flexible_five_days_counts_five_days(self):
        resource = self._resource(name="Fully flexible", calendar_id=False)
        data = self.calendar._get_attendance_intervals_days_data(
            self.calendar._attendance_intervals_batch(
                datetime(2026, 3, 2, 8, 0).replace(tzinfo=UTC),
                datetime(2026, 3, 6, 17, 0).replace(tzinfo=UTC),
                resource,
            )[resource.id]
        )
        self.assertEqual(
            data["days"],
            5.0,
            "a fully flexible resource absent Mon-Fri is absent five days, not"
            " the wall-clock fraction 4.375",
        )

    def test_fully_flexible_availability_is_unchanged(self):
        resource = self._resource(name="Still free", calendar_id=False)
        start = datetime(2026, 3, 2, 0, 0).replace(tzinfo=UTC)
        end = datetime(2026, 3, 7, 0, 0).replace(tzinfo=UTC)
        intervals = self.calendar._attendance_intervals_batch(start, end, resource)[
            resource.id
        ]
        covered = sum(
            (stop - begin).total_seconds() for begin, stop, _meta in intervals
        )
        self.assertEqual(
            covered,
            (end - start).total_seconds(),
            "every instant of the window must still be available",
        )

    def test_fully_flexible_partial_day_is_a_fraction_of_a_working_day(self):
        resource = self._resource(name="Part day", calendar_id=False)
        data = self.calendar._get_attendance_intervals_days_data(
            self.calendar._attendance_intervals_batch(
                datetime(2026, 3, 2, 9, 0).replace(tzinfo=UTC),
                datetime(2026, 3, 2, 13, 0).replace(tzinfo=UTC),
                resource,
            )[resource.id]
        )
        self.assertEqual(data["days"], 0.5)

    def test_fully_flexible_long_day_is_capped_at_one_day(self):
        resource = self._resource(name="Long day", calendar_id=False)
        data = self.calendar._get_attendance_intervals_days_data(
            self.calendar._attendance_intervals_batch(
                datetime(2026, 3, 2, 8, 0).replace(tzinfo=UTC),
                datetime(2026, 3, 3, 0, 0).replace(tzinfo=UTC),
                resource,
            )[resource.id]
        )
        self.assertEqual(data["days"], 1.0)

    def test_fully_flexible_day_count_survives_dst(self):
        resource = self._resource(name="DST", calendar_id=False, tz="Europe/Brussels")
        brussels = timezone("Europe/Brussels")
        start = datetime(2026, 3, 28, 0, 0).replace(tzinfo=brussels)
        end = datetime(2026, 3, 31, 0, 0).replace(tzinfo=brussels)
        data = self.calendar._get_attendance_intervals_days_data(
            self.calendar._attendance_intervals_batch(start, end, resource)[resource.id]
        )
        self.assertEqual(data["days"], 3.0)

    def test_allocation_mixin_triggers_on_allocated_percentage(self):
        projection = self.env["mixin.resource.scheduling"]._get_fields_sync_trigger()
        self.assertNotIn("allocated_percentage", projection)

        allocation = self.env["mixin.resource.allocation"]._get_fields_sync_trigger()
        self.assertIn("allocated_percentage", allocation)

    def test_calendar_override_applies_to_a_flexible_resource(self):
        flexible = self.env["resource.calendar"].create(
            {
                "name": "flex 20h",
                "company_id": self.company.id,
                "tz": "UTC",
                "schedule_type": "flexible",
                "hours_per_week": 20.0,
                "hours_per_day": 4.0,
            }
        )
        resource = self._resource(name="Flexible", calendar_id=flexible.id)
        reservation = self.env["resource.reservation"].create(
            {
                "name": "override me",
                "resource_id": resource.id,
                "date_start": datetime(2026, 3, 2, 0, 0),
                "date_end": datetime(2026, 3, 6, 23, 59),
            }
        )
        native = reservation._scheduling_get_work_hours(
            reservation.date_start, reservation.date_end, resource=resource
        )
        overridden = reservation._scheduling_get_work_hours(
            reservation.date_start,
            reservation.date_end,
            resource=resource,
            calendar=self.calendar,
        )
        self.assertNotEqual(
            native,
            overridden,
            "an explicit calendar must override the resource's own, on every path",
        )
        self.assertEqual(overridden, 40.0)

    def _conflicting_pair(self):
        resource = self._resource(name="Double booked")
        vals = {
            "resource_id": resource.id,
            "date_start": datetime(2026, 3, 2, 8, 0),
            "date_end": datetime(2026, 3, 2, 12, 0),
        }
        first = self.env["resource.reservation"].create({"name": "first", **vals})
        second = self.env["resource.reservation"].create({"name": "second", **vals})
        return first, second

    def test_conflicts_are_searchable(self):
        first, second = self._conflicting_pair()
        found = self.env["resource.reservation"].search(
            [("schedule_overlap_count", ">", 0)]
        )
        self.assertLessEqual({first.id, second.id}, set(found.ids))

    def test_conflict_free_reservations_are_searchable_too(self):
        first, _second = self._conflicting_pair()
        alone = self.env["resource.reservation"].create(
            {
                "name": "alone",
                "resource_id": self._resource(name="Solo").id,
                "date_start": datetime(2026, 3, 3, 8, 0),
                "date_end": datetime(2026, 3, 3, 12, 0),
            }
        )
        clean = self.env["resource.reservation"].search(
            [("schedule_overlap_count", "=", 0)]
        )
        self.assertIn(alone.id, clean.ids)
        self.assertNotIn(first.id, clean.ids)

    def test_search_and_compute_agree(self):
        first, second = self._conflicting_pair()
        for reservation in (first, second):
            found = self.env["resource.reservation"].search(
                [
                    ("id", "=", reservation.id),
                    ("schedule_overlap_count", "=", reservation.schedule_overlap_count),
                ]
            )
            self.assertEqual(found, reservation)

    def test_cross_company_leave_is_rejected(self):
        other_company = self.env["res.company"].create({"name": "Other SP Co"})
        other_calendar = self.env["resource.calendar"].create(
            {"name": "other", "company_id": other_company.id, "tz": "UTC"}
        )
        resource = self._resource(name="Company A resource")
        with self.assertRaises(UserError) as caught:
            leave = self.env["resource.schedule.exception"].create(
                {
                    "name": "cross company",
                    "calendar_id": other_calendar.id,
                    "resource_id": resource.id,
                    "date_from": datetime(2026, 3, 2, 8, 0),
                    "date_to": datetime(2026, 3, 2, 17, 0),
                }
            )
            leave.flush_recordset()
        self.assertIn("compan", str(caught.exception).lower())

    def test_company_less_calendar_is_valid_for_any_resource(self):
        shared = self.env["resource.calendar"].create(
            {"name": "shared", "company_id": False, "tz": "UTC"}
        )
        resource = self._resource(name="Shared cal", calendar_id=shared.id)
        resource.flush_recordset()
        self.assertEqual(resource.calendar_id, shared)

    def _global_leave(self, calendar):
        return self.env["resource.schedule.exception"].create(
            {
                "name": "Public holiday",
                "calendar_id": calendar.id,
                "date_from": datetime(2026, 3, 2, 8, 0),
                "date_to": datetime(2026, 3, 2, 17, 0),
            }
        )

    def _sees_leave(self, resource):
        return bool(
            self.calendar._leave_intervals_batch(
                datetime(2026, 3, 1).replace(tzinfo=UTC),
                datetime(2026, 3, 8).replace(tzinfo=UTC),
                resource,
            )[resource.id]
        )

    def test_company_less_resource_sees_global_leaves(self):
        shared_calendar = self.env["resource.calendar"].create(
            {"name": "shared cal", "company_id": False, "tz": "UTC"}
        )
        resource = self._resource(
            name="No company", company_id=False, calendar_id=shared_calendar.id
        )
        leave = self._global_leave(shared_calendar)
        self.env.flush_all()
        self.assertTrue(leave.company_id, "precondition: the leave names a company")
        self.assertFalse(resource.company_id)
        self.assertTrue(
            bool(
                shared_calendar._leave_intervals_batch(
                    datetime(2026, 3, 1).replace(tzinfo=UTC),
                    datetime(2026, 3, 8).replace(tzinfo=UTC),
                    resource,
                )[resource.id]
            )
        )

    def test_a_leave_cannot_be_stranded_in_another_company(self):
        other_company = self.env["res.company"].create({"name": "Stranded Co"})
        other_calendar = self.env["resource.calendar"].create(
            {"name": "stranded", "company_id": other_company.id, "tz": "UTC"}
        )
        with self.assertRaises(UserError):
            self.env["resource.schedule.exception"].create(
                {
                    "name": "stranded",
                    "calendar_id": other_calendar.id,
                    "resource_id": self._resource(name="Local").id,
                    "date_from": datetime(2026, 3, 2, 8, 0),
                    "date_to": datetime(2026, 3, 2, 17, 0),
                }
            ).flush_recordset()

    def test_global_leave_still_stops_at_a_company_boundary(self):
        other_company = self.env["res.company"].create({"name": "Boundary Co"})
        other_calendar = self.env["resource.calendar"].create(
            {"name": "boundary", "company_id": other_company.id, "tz": "UTC"}
        )
        resource = self._resource(
            name="Boundary", company_id=other_company.id, calendar_id=other_calendar.id
        )
        self._global_leave(self.calendar)
        self.env.flush_all()
        self.assertFalse(
            self._sees_leave(resource),
            "a holiday declared by one named company must not reach another's",
        )

    def test_same_company_leave_is_accepted(self):
        resource = self._resource(name="Same company resource")
        leave = self.env["resource.schedule.exception"].create(
            {
                "name": "in company",
                "calendar_id": self.calendar.id,
                "resource_id": resource.id,
                "date_from": datetime(2026, 3, 2, 8, 0),
                "date_to": datetime(2026, 3, 2, 17, 0),
            }
        )
        leave.flush_recordset()
        self.assertEqual(leave.company_id, self.company)

    def test_work_resources_count_reacts_to_new_resources(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "counted", "company_id": self.company.id, "tz": "UTC"}
        )
        self.assertEqual(calendar.work_resources_count, 0)
        self._resource(name="Counted", calendar_id=calendar.id)
        self.assertEqual(calendar.work_resources_count, 1)

    def test_two_weeks_explanation_agrees_with_the_section_labels(self):
        calendar = self.env["resource.calendar"].create(
            {"name": "explained", "company_id": self.company.id, "tz": "UTC"}
        )
        attendance_model = self.env["resource.calendar.attendance"]
        for tz_name in ("Pacific/Kiritimati", "Pacific/Midway"):
            scoped = calendar.with_context(tz=tz_name)
            scoped.invalidate_recordset(["two_weeks_explanation"])
            local_today = fields.Date.context_today(scoped)
            expected = (
                "the second"
                if attendance_model.get_week_type(local_today)
                else "the first"
            )
            self.assertIn(
                expected,
                scoped.two_weeks_explanation,
                f"explanation disagrees with the week the labels show in {tz_name}",
            )

    def test_calendar_tz_default_survives_a_missing_admin_xmlid(self):
        self.env.user.tz = False
        calendar_model = self.env["resource.calendar"].with_context(tz=False)

        real_ref = type(self.env).ref

        def ref_without_admin(env_self, xmlid, raise_if_not_found=True):
            if xmlid == "base.user_admin":
                if raise_if_not_found:
                    raise ValueError(xmlid)
                return None
            return real_ref(env_self, xmlid, raise_if_not_found=raise_if_not_found)

        self.patch(type(self.env), "ref", ref_without_admin)
        self.assertEqual(calendar_model._default_tz(), "UTC")
        self.assertTrue(
            calendar_model.create({"name": "no admin", "company_id": self.company.id})
        )
