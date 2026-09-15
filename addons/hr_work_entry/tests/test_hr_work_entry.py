from datetime import date, datetime

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestHrWorkEntry(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].create({"name": "Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})
        cls.env.user.company_ids = [(6, 0, [cls.company_a.id, cls.company_b.id])]
        cls.env.user.company_id = cls.company_a.id
        cls.employee_a = cls.env["hr.employee"].create(
            {
                "name": "Employee A",
                "company_id": cls.company_a.id,
                "contract_date_start": "2023-01-01",
                "date_version": "2023-01-01",
            }
        )
        cls.employee_a_first_version = cls.employee_a.version_ids[0]
        cls.employee_b = cls.env["hr.employee"].create(
            {
                "name": "Employee B",
                "company_id": cls.company_b.id,
                "contract_date_start": "2023-01-01",
                "date_version": "2023-01-01",
            }
        )
        cls.work_entry_type = cls.env["hr.work.entry.type"].create(
            {
                "name": "Attendance",
                "code": "ATTEND",
            }
        )

    def test_work_entry_company_from_employee(self):
        work_entry = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry",
                "employee_id": self.employee_b.id,
                "work_entry_type_id": self.work_entry_type.id,
                "date": date(2024, 1, 1),
                "duration": 8,
            }
        )
        self.assertEqual(
            work_entry.company_id,
            self.employee_b.company_id,
            "Work entry should use the employee's company not the current user's company.",
        )

    def test_work_entry_conflict_no_we_type(self):
        work_entry = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry",
                "work_entry_type_id": False,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 8,
            }
        )
        self.assertEqual(
            work_entry.state,
            "conflict",
            "Work entry should conflict with no work entry type.",
        )
        work_entry = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry",
                "work_entry_type_id": self.work_entry_type.id,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 8,
            }
        )
        self.assertEqual(
            work_entry.state,
            "draft",
            "Work entry should not conflict with a work entry type.",
        )
        work_entry.write({"work_entry_type_id": False})
        self.assertEqual(
            work_entry.state,
            "conflict",
            "Work entry should conflict with no work entry type.",
        )

    def test_work_entry_conflict_sum_duration(self):
        with self.assertRaises(ValidationError), mute_logger("odoo.db"):
            self.env["hr.work.entry"].create(
                {
                    "name": "Test Work Entry",
                    "work_entry_type_id": False,
                    "employee_id": self.employee_b.id,
                    "date": date(2024, 1, 1),
                    "duration": 0,
                }
            )

        work_entry = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry",
                "work_entry_type_id": self.work_entry_type.id,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 8,
            }
        )
        self.assertEqual(
            work_entry.state,
            "draft",
            "Work entry should be in draft.",
        )
        work_entry_2 = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry 2",
                "work_entry_type_id": self.work_entry_type.id,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 17,
            }
        )
        self.assertEqual(
            (work_entry | work_entry_2).mapped("state"),
            ["conflict", "conflict"],
            "Work entries with a total duration for a same day <= 0h or > 24h should conflict.",
        )
        work_entry_2.write(
            {
                "duration": 16,
            }
        )
        self.assertEqual(
            (work_entry | work_entry_2).mapped("state"),
            ["draft", "draft"],
            "Work entries with a total duration for a same day > 0h and <= 24h should not conflict.",
        )

    def test_write_state_draft_rechecks_conflict(self):
        work_entry = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry",
                "work_entry_type_id": self.work_entry_type.id,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 8,
            }
        )
        work_entry_2 = self.env["hr.work.entry"].create(
            {
                "name": "Test Work Entry 2",
                "work_entry_type_id": self.work_entry_type.id,
                "employee_id": self.employee_b.id,
                "date": date(2024, 1, 1),
                "duration": 17,
            }
        )
        self.assertEqual(
            (work_entry | work_entry_2).mapped("state"),
            ["conflict", "conflict"],
            "Work entries with a total duration for a same day > 24h should conflict.",
        )
        work_entry.write({"state": "draft"})
        self.assertEqual(
            (work_entry | work_entry_2).mapped("state"),
            ["conflict", "conflict"],
            "Reactivating one entry must re-run conflict detection: the day is "
            "still over 24h, so both entries must remain (or return to) conflict, "
            "not silently stay/become draft.",
        )

    def test_check_code_unicity_scoped_to_own_country(self):
        country_be = self.env.ref("base.be")
        country_fr = self.env.ref("base.fr")
        self.env["hr.work.entry.type"].create(
            {"name": "Existing FR", "code": "SHARED", "country_id": country_fr.id}
        )
        self.env["hr.work.entry.type"].create(
            [
                {"name": "New BE", "code": "SHARED", "country_id": country_be.id},
                {"name": "New FR", "code": "OTHER", "country_id": country_fr.id},
            ]
        )

    def test_reset_regenerates_the_whole_day(self):
        self.employee_b.tz = "Europe/Brussels"
        self.employee_b.resource_calendar_id.tz = "Europe/Brussels"
        generated = self.employee_b.generate_work_entries(
            date(2024, 2, 5), date(2024, 2, 9)
        )
        day = generated.filtered(lambda w: w.date == date(2024, 2, 6))
        self.assertTrue(day)
        day.write({"work_entry_type_id": self.work_entry_type.id})
        manual = self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee_b.id,
                "date": date(2024, 2, 6),
                "duration": 2,
                "work_entry_type_id": self.work_entry_type.id,
            }
        )

        self.env["hr.work.entry.regeneration.wizard"].regenerate_work_entries(
            slots=[{"employee_id": self.employee_b.id, "date": "2024-02-06"}]
        )

        self.assertFalse(day.exists().filtered("active"))
        self.assertFalse(manual.active, "Resetting a day discards manual edits.")
        regenerated = self.env["hr.work.entry"].search(
            [("employee_id", "=", self.employee_b.id), ("date", "=", date(2024, 2, 6))]
        )
        self.assertEqual(
            regenerated.work_entry_type_id,
            self.env.ref("hr_work_entry.work_entry_type_attendance"),
            "Resetting a day must regenerate it from the schedule. An earlier "
            "version only archived the selected entries and left the day empty, "
            "and a plain generation could not backfill it because the version's "
            "generated range already covered the day.",
        )
        self.assertEqual(sum(regenerated.mapped("duration")), 8)

    def test_reset_slots_skips_a_validated_day(self):
        self.employee_b.tz = "Europe/Brussels"
        self.employee_b.resource_calendar_id.tz = "Europe/Brussels"
        generated = self.employee_b.generate_work_entries(
            date(2024, 2, 5), date(2024, 2, 9)
        )
        validated_day = generated.filtered(lambda w: w.date == date(2024, 2, 6))
        other_day = generated.filtered(lambda w: w.date == date(2024, 2, 7))
        validated_day.action_validate()

        self.env["hr.work.entry.regeneration.wizard"].regenerate_work_entries(
            slots=[
                {"employee_id": self.employee_b.id, "date": "2024-02-06"},
                {"employee_id": self.employee_b.id, "date": "2024-02-07"},
            ]
        )

        self.assertEqual(
            validated_day.exists(),
            validated_day,
            "The validated entry must survive untouched.",
        )
        self.assertTrue(
            validated_day.active,
            "The validated entry must stay active, not archived.",
        )
        same_day_entries = self.env["hr.work.entry"].search(
            [("employee_id", "=", self.employee_b.id), ("date", "=", date(2024, 2, 6))]
        )
        self.assertEqual(
            same_day_entries,
            validated_day,
            "Resetting a slot list must not create a duplicate active entry "
            "alongside an already-validated day, even when another slot in the "
            "same call is a legitimate, non-validated day.",
        )
        self.assertFalse(
            other_day.exists().filtered("active"),
            "A non-validated day in the same slot list must still be reset.",
        )

    def test_recompute_with_validated_entries_leaves_other_employees_alone(self):
        self.employee_a.generate_work_entries(date(2024, 4, 1), date(2024, 4, 30))
        other_entries = self.employee_b.generate_work_entries(
            date(2024, 4, 1), date(2024, 4, 30)
        )
        validated = self.env["hr.work.entry"].search(
            [("employee_id", "=", self.employee_a.id)], limit=1
        )
        validated.action_validate()

        self.employee_a.version_id.write(
            {"resource_calendar_id": self.env.company.resource_calendar_id.copy().id}
        )

        self.assertTrue(
            all(other_entries.exists().mapped("active")),
            "Recomputing one employee's work entries must never touch another "
            "employee. When every selected employee is skipped for holding a "
            "validated entry, the wizard used to call generate_work_entries on an "
            "empty recordset, which means every employee of the database.",
        )

    def test_fully_flexible_employee_days_use_one_timezone(self):
        company_calendar = self.env.company.resource_calendar_id
        company_calendar.tz = "America/Los_Angeles"
        employee = self.env["hr.employee"].create(
            {
                "name": "Tokyo",
                "tz": "Asia/Tokyo",
                "contract_date_start": "2024-01-01",
                "date_version": "2024-01-01",
                "resource_calendar_id": False,
            }
        )
        work_entries = employee.generate_work_entries(
            date(2024, 1, 8), date(2024, 1, 10)
        )
        self.assertEqual(
            [(w.date, w.duration) for w in work_entries.sorted("date")],
            [
                (date(2024, 1, 8), 24.0),
                (date(2024, 1, 9), 24.0),
                (date(2024, 1, 10), 24.0),
            ],
            "A fully flexible employee has no calendar of their own, so the day "
            "boundaries and the dates stamped on the entries must both use the "
            "same fallback timezone (the company calendar's). Computing the "
            "boundaries in the employee's timezone and the dates in the company "
            "calendar's produced a 17h and a 7h entry on the neighbouring days.",
        )

    def test_new_version_starts_with_an_empty_generated_range(self):
        self.employee_a.generate_work_entries(date(2024, 3, 1), date(2024, 3, 31))
        first = self.employee_a.version_id
        self.assertLess(first.date_generated_from, first.date_generated_to)
        for version in (
            self.employee_a.create_version({"date_version": date(2024, 3, 15)}),
            first.copy({"date_version": date(2024, 6, 1)}),
        ):
            self.assertEqual(
                version.date_generated_from,
                version.date_generated_to,
                "A new version has generated nothing yet; inheriting the source "
                "version's range would make the generator skip it forever.",
            )
            self.assertFalse(version.last_generation_date)

    def test_split_keeps_the_total_and_returns_a_draft(self):
        entry = self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee_b.id,
                "date": date(2024, 5, 6),
                "duration": 8,
                "work_entry_type_id": self.work_entry_type.id,
            }
        )
        with self.assertRaises(UserError):
            entry.action_split({"duration": -2})
        with self.assertRaises(UserError):
            entry.action_split({"duration": 8})
        other_type = self.env["hr.work.entry.type"].create(
            {"name": "Other", "code": "OTHER_SPLIT"}
        )
        split = self.env["hr.work.entry"].browse(
            entry.action_split(
                {"duration": 3, "work_entry_type_id": other_type.id, "name": "half"}
            )
        )
        self.assertEqual((entry.duration, split.duration), (5, 3))
        self.assertEqual(split.work_entry_type_id, other_type)
        self.assertEqual(split.name, "half")
        self.assertEqual((entry.state, split.state), ("draft", "draft"))

    def test_generation_ignores_another_company_global_leave(self):
        leave_type = self.env.ref("hr_work_entry.work_entry_type_leave")
        self.env["resource.schedule.exception"].with_company(self.company_b).create(
            {
                "name": "Company B shutdown",
                "date_from": "2024-01-03 00:00:00",
                "date_to": "2024-01-03 23:59:59",
                "calendar_id": False,
                "work_entry_type_id": leave_type.id,
            }
        )
        vals_list = self.employee_a.version_id._prepare_work_entries_values(
            datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 5, 23, 59, 59)
        )
        january_third = [
            vals for vals in vals_list if vals["date_start"].date() == date(2024, 1, 3)
        ]
        self.assertTrue(january_third)
        self.assertNotIn(
            leave_type.id,
            {vals["work_entry_type_id"] for vals in january_third},
            "A global time off of company B must not reach company A's employee. "
            "The leave lookup used to filter on env.companies, which is every "
            "company the caller may act in: the cron narrows that to one company, "
            "but a leave approval or an attendance runs it in the user's own "
            "environment, where it spans all of them.",
        )

    def test_set_to_draft_rechecks_the_reactivated_entry(self):
        first = self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee_b.id,
                "date": date(2024, 5, 7),
                "duration": 8,
                "work_entry_type_id": self.work_entry_type.id,
            }
        )
        second = self.env["hr.work.entry"].create(
            {
                "employee_id": self.employee_b.id,
                "date": date(2024, 5, 7),
                "duration": 8,
                "work_entry_type_id": self.work_entry_type.id,
            }
        )
        (first | second).action_validate()

        first.action_set_to_draft()

        self.assertEqual(
            first.state,
            "conflict",
            "The day still holds a validated entry, so the reactivated one cannot "
            "be validated again on its own; the write must re-check the entry it "
            "reactivates, not only its siblings.",
        )
        second.action_set_to_draft()
        self.assertEqual((first.state, second.state), ("draft", "draft"))

    def test_leave_on_a_non_working_day_conflicts_whatever_the_calendar_timezone(self):
        leave_type = self.env.ref("hr_work_entry.work_entry_type_leave")
        for tz in ("America/Los_Angeles", "Asia/Tokyo"):
            calendar = self.env.company.resource_calendar_id.copy({"tz": tz})
            employee = self.env["hr.employee"].create(
                {
                    "name": tz,
                    "contract_date_start": "2024-01-01",
                    "date_version": "2024-01-01",
                    "resource_calendar_id": calendar.id,
                }
            )
            saturday = self.env["hr.work.entry"].create(
                {
                    "employee_id": employee.id,
                    "date": date(2024, 1, 13),
                    "duration": 8,
                    "work_entry_type_id": leave_type.id,
                }
            )
            monday = self.env["hr.work.entry"].create(
                {
                    "employee_id": employee.id,
                    "date": date(2024, 1, 15),
                    "duration": 8,
                    "work_entry_type_id": leave_type.id,
                }
            )
            self.assertEqual((saturday.state, monday.state), ("conflict", "draft"), tz)

    def test_nullify_work_entry_tz(self):
        self.employee_a.tz = "Europe/Brussels"
        self.employee_a.resource_calendar_id.tz = "Europe/Brussels"

        january_work_entries = self.employee_a.generate_work_entries(
            date(2024, 1, 1), date(2024, 1, 31), force=True
        )
        self.employee_a.generate_work_entries(
            date(2024, 2, 1), date(2024, 2, 28), force=True
        )

        new_january_work_entries = self.env["hr.work.entry"].search(
            [
                ("employee_id", "=", self.employee_a.id),
                ("date", ">=", date(2024, 1, 1)),
                ("date", "<=", date(2024, 1, 31)),
            ]
        )
        self.assertEqual(january_work_entries, new_january_work_entries)

    def test_nullify_work_entry(self):
        january_work_entries = self.employee_a.generate_work_entries(
            date(2024, 1, 1), date(2024, 1, 31)
        )
        self.assertTrue(
            all(
                we.version_id == self.employee_a_first_version
                for we in january_work_entries
            )
        )

        second_version = self.employee_a.create_version(
            {"date_version": date(2023, 12, 1)}
        )
        self.employee_a.generate_work_entries(date(2024, 1, 1), date(2024, 1, 31))

        all_january_work_entries = self.env["hr.work.entry"].search(
            [
                ("employee_id", "=", self.employee_a.id),
                ("date", ">=", date(2024, 1, 1)),
                ("date", "<=", date(2024, 1, 31)),
            ]
        )

        self.assertEqual(len(all_january_work_entries), 23)
        self.assertTrue(
            all(we.version_id == second_version for we in all_january_work_entries)
        )

    def test_work_entry_version_id(self):
        second_version = self.employee_a.create_version(
            {"date_version": date(2023, 12, 1)}
        )

        v1_we, v2_we = self.env["hr.work.entry"].create(
            [
                {
                    "date": date(2023, 10, 1),
                    "employee_id": self.employee_a.id,
                },
                {
                    "date": date(2024, 1, 1),
                    "employee_id": self.employee_a.id,
                },
            ]
        )
        self.assertEqual(v1_we.version_id, self.employee_a_first_version)
        self.assertEqual(v2_we.version_id, second_version)
