from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import common


class TestTimesheetGlobalTimeOff(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.test_company = self.env["res.company"].create(
            {
                "name": "My Test Company",
            }
        )

        attendance_ids = [
            (
                0,
                0,
                {
                    "name": "Monday Morning",
                    "dayofweek": "0",
                    "hour_from": 9,
                    "hour_to": 12,
                    "day_period": "morning",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Monday Lunch",
                    "dayofweek": "0",
                    "hour_from": 12,
                    "hour_to": 13,
                    "day_period": "lunch",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Monday Afternoon",
                    "dayofweek": "0",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Tuesday Morning",
                    "dayofweek": "1",
                    "hour_from": 9,
                    "hour_to": 12,
                    "day_period": "morning",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Tuesday Lunch",
                    "dayofweek": "1",
                    "hour_from": 12,
                    "hour_to": 13,
                    "day_period": "lunch",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Tuesday Afternoon",
                    "dayofweek": "1",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Thursday Morning",
                    "dayofweek": "3",
                    "hour_from": 9,
                    "hour_to": 12,
                    "day_period": "morning",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Thursday Lunch",
                    "dayofweek": "3",
                    "hour_from": 12,
                    "hour_to": 13,
                    "day_period": "lunch",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Thursday Afternoon",
                    "dayofweek": "3",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Friday Morning",
                    "dayofweek": "4",
                    "hour_from": 9,
                    "hour_to": 12,
                    "day_period": "morning",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Friday Lunch",
                    "dayofweek": "4",
                    "hour_from": 12,
                    "hour_to": 13,
                    "day_period": "lunch",
                },
            ),
            (
                0,
                0,
                {
                    "name": "Friday Afternoon",
                    "dayofweek": "4",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                },
            ),
        ]

        self.part_time_calendar, self.part_time_calendar2 = self.env[
            "resource.calendar"
        ].create(
            [
                {
                    "name": "Part Time Calendar",
                    "company_id": self.test_company.id,
                    "hours_per_day": 6,
                    "attendance_ids": attendance_ids,
                },
                {
                    "name": "Night Watch",
                    "company_id": self.test_company.id,
                    "hours_per_day": 6,
                    "attendance_ids": attendance_ids,
                },
            ]
        )
        (
            self.full_time_employee,
            self.full_time_employee_2,
            self.part_time_employee,
            self.part_time_employee2,
        ) = self.env["hr.employee"].create(
            [
                {
                    "name": "John Doe",
                    "company_id": self.test_company.id,
                    "resource_calendar_id": self.test_company.resource_calendar_id.id,
                },
                {
                    "name": "John Smith",
                    "company_id": self.test_company.id,
                    "resource_calendar_id": self.test_company.resource_calendar_id.id,
                },
                {
                    "name": "Jane Doe",
                    "company_id": self.test_company.id,
                    "resource_calendar_id": self.part_time_calendar.id,
                },
                {
                    "name": "Jon Show",
                    "company_id": self.test_company.id,
                    "resource_calendar_id": self.part_time_calendar2.id,
                },
            ]
        )

        self.test_company_2 = self.env["res.company"].create(
            {
                "name": "My Test Company 2",
            }
        )

    def _get_timesheets_by_employee(self, leave_task):
        timesheets_by_read_dict = self.env["account.analytic.line"]._read_group(
            [("task_id", "=", leave_task.id)], ["employee_id"], ["__count"]
        )
        return {timesheet.id: count for timesheet, count in timesheets_by_read_dict}

    def test_timesheet_creation_and_deletion_for_time_off(self):
        leave_start_datetime = datetime(2021, 1, 4, 7, 0, 0, 0)
        leave_end_datetime = datetime(2021, 1, 8, 18, 0, 0, 0)

        global_time_off = self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": leave_start_datetime,
                "date_to": leave_end_datetime,
            }
        )

        leave_task = self.test_company.leave_timesheet_task_id

        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)
        self.assertFalse(timesheets_by_employee.get(self.part_time_employee.id, False))
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee.id), 5)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee_2.id), 5)

        self.assertEqual(leave_task.effective_hours, 80)

        global_time_off.unlink()

        self.assertFalse(leave_task.timesheet_ids.ids)

    @freeze_time("2022-01-01 08:00:00")
    def test_timesheet_creation_and_deletion_on_employee_archive(self):
        today = datetime.today()
        leave_start_datetime = today + timedelta(days=-today.weekday(), weeks=1)
        leave_end_datetime = leave_start_datetime + timedelta(days=5)

        self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": leave_start_datetime,
                "date_to": leave_end_datetime,
            }
        )

        self.env["resource.schedule.exception"].with_company(self.test_company).create(
            {
                "name": "Global leave",
                "calendar_id": False,
                "date_from": (leave_start_datetime + timedelta(weeks=1)).replace(
                    hour=0, minute=0, second=0
                ),
                "date_to": (leave_start_datetime + timedelta(weeks=1, days=1)).replace(
                    hour=23, minute=59, second=59
                ),
            }
        )

        self.env["resource.schedule.exception"].with_company(
            self.test_company_2
        ).create(
            {
                "name": "Global leave in another company",
                "calendar_id": False,
                "date_from": (leave_start_datetime + timedelta(weeks=2)).replace(
                    hour=0, minute=0, second=0
                ),
                "date_to": (leave_start_datetime + timedelta(weeks=2)).replace(
                    hour=23, minute=59, second=59
                ),
            }
        )

        timesheets_full_time_employee = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.full_time_employee.id)]
        )
        self.assertEqual(len(timesheets_full_time_employee), 7)

        self.full_time_employee.active = False
        timesheets_full_time_employee = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.full_time_employee.id)]
        )
        self.assertEqual(len(timesheets_full_time_employee), 0)

        self.full_time_employee.active = True
        timesheets_full_time_employee = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.full_time_employee.id)]
        )
        self.assertEqual(len(timesheets_full_time_employee), 7)

    def test_reactivation_names_lines_with_the_real_day_total(self):
        """A regenerated public-holiday line is "Time Off (i/n)", never (i/0).

        `_work_time_per_day` returns `{calendar_id: {leave_id: [(date, hours)]}}`.
        `_create_future_public_holidays_timesheets` used to hand
        `work_hours_data[global_time_off.id]` to the line-name builder as the
        total -- a leave id read at the calendar level, which a `defaultdict`
        answers with an empty mapping instead of raising. Every line the
        reactivation path produced was therefore named "Time Off (1/0)".
        Nothing failed, because no test asserted a name.
        """
        today = datetime.today()
        leave_start_datetime = today + timedelta(days=-today.weekday(), weeks=1)

        self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": leave_start_datetime,
                "date_to": leave_start_datetime + timedelta(days=5),
            }
        )

        self.full_time_employee.active = False
        self.full_time_employee.active = True

        timesheets = self.env["account.analytic.line"].search(
            [
                ("employee_id", "=", self.full_time_employee.id),
                ("global_leave_id", "!=", False),
            ]
        )
        self.assertTrue(timesheets, "the reactivation must regenerate the lines")
        for leave, lines in timesheets.grouped("global_leave_id").items():
            totals = {int(line.name.rsplit("/", 1)[1].rstrip(")")) for line in lines}
            self.assertEqual(
                totals,
                {len(lines)},
                f"every line of {leave.name} must state the real day total",
            )

    def test_no_timesheet_on_off_days(self):
        leave_start_datetime = datetime(2021, 1, 4, 7, 0, 0, 0)
        leave_end_datetime = datetime(2021, 1, 8, 18, 0, 0, 0)
        day_off = datetime(2021, 1, 6, 0, 0, 0)

        self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.part_time_calendar.id,
                "date_from": leave_start_datetime,
                "date_to": leave_end_datetime,
            }
        )

        leave_task = self.test_company.leave_timesheet_task_id
        self.assertEqual(
            leave_task.effective_hours, 4 * self.part_time_calendar.hours_per_day
        )

        timesheet = self.env["account.analytic.line"].search(
            [("date", "=", day_off), ("task_id", "=", leave_task.id)]
        )
        self.assertFalse(timesheet.id)

    def test_timesheet_creation_and_deletion_for_calendar_set_and_remove(self):
        leave_start_datetime = datetime(2021, 1, 4, 7, 0, 0, 0)
        leave_end_datetime = datetime(2021, 1, 8, 18, 0, 0, 0)

        global_time_off = self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": leave_start_datetime,
                "date_to": leave_end_datetime,
            }
        )

        leave_task = self.test_company.leave_timesheet_task_id

        global_time_off.calendar_id = False

        self.assertFalse(leave_task.timesheet_ids.ids)

        global_time_off.calendar_id = self.test_company.resource_calendar_id.id

        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)
        self.assertFalse(timesheets_by_employee.get(self.part_time_employee.id, False))
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee.id), 5)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee_2.id), 5)

        self.assertEqual(leave_task.effective_hours, 80)

    def test_timeoff_task_creation_with_global_leave(self):
        task_count = self.env["project.task"].search_count(
            [("is_timeoff_task", "!=", False)]
        )

        self.env["resource.schedule.exception"].create(
            {
                "name": "Test",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": datetime(2021, 1, 4, 7, 0, 0, 0),
                "date_to": datetime(2021, 1, 8, 18, 0, 0, 0),
            }
        )

        new_task_count = self.env["project.task"].search_count(
            [("is_timeoff_task", "!=", False)]
        )
        self.assertEqual(task_count + 1, new_task_count)

    def test_timesheet_creation_for_global_time_off_wo_calendar(self):
        leave_start_datetime = datetime(2021, 1, 4, 7, 0)
        leave_end_datetime = datetime(2021, 1, 8, 18, 0)

        global_time_off = (
            self.env["resource.schedule.exception"]
            .with_company(self.test_company)
            .create(
                {
                    "name": "Test",
                    "calendar_id": False,
                    "date_from": leave_start_datetime,
                    "date_to": leave_end_datetime,
                }
            )
        )

        leave_task = self.test_company.leave_timesheet_task_id
        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)
        self.assertEqual(timesheets_by_employee.get(self.part_time_employee.id), 4)
        self.assertEqual(timesheets_by_employee.get(self.part_time_employee2.id), 4)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee.id), 5)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee_2.id), 5)
        self.assertEqual(leave_task.effective_hours, 128)

        global_time_off.calendar_id = self.test_company.resource_calendar_id.id
        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)

        self.assertFalse(timesheets_by_employee.get(self.part_time_employee.id, False))
        self.assertFalse(timesheets_by_employee.get(self.part_time_employee2.id, False))
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee.id), 5)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee_2.id), 5)
        self.assertEqual(leave_task.effective_hours, 80)

    def test_timesheet_creation_for_global_time_off_in_differant_company(self):
        leave_start_datetime = datetime(2021, 1, 4, 7, 0)
        leave_end_datetime = datetime(2021, 1, 8, 18, 0)

        new_company = self.env["res.company"].create(
            {
                "name": "Winterfell",
            }
        )

        self.env["resource.schedule.exception"].with_company(new_company).create(
            {
                "name": "Test",
                "calendar_id": False,
                "date_from": leave_start_datetime,
                "date_to": leave_end_datetime,
            }
        )

        leave_task = self.test_company.leave_timesheet_task_id
        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)
        self.assertFalse(timesheets_by_employee.get(self.part_time_employee, False))
        self.assertFalse(timesheets_by_employee.get(self.full_time_employee, False))
        self.assertEqual(leave_task.effective_hours, 0)

    def test_timesheet_creation_for_global_time_off_wo_calendar_in_batch(self):
        self.env["resource.schedule.exception"].with_company(self.test_company).create(
            [
                {
                    "name": "Easter Monday",
                    "calendar_id": False,
                    "date_from": datetime(2022, 4, 18, 5, 0, 0),
                    "date_to": datetime(2022, 4, 18, 18, 0, 0),
                    "resource_id": False,
                },
                {
                    "name": "Ascension Day",
                    "calendar_id": False,
                    "date_from": datetime(2022, 4, 26, 5, 0, 0),
                    "date_to": datetime(2022, 4, 26, 18, 0, 0),
                },
            ]
        )

        leave_task = self.test_company.leave_timesheet_task_id
        timesheets_by_employee = self._get_timesheets_by_employee(leave_task)

        self.assertEqual(timesheets_by_employee.get(self.part_time_employee.id), 2)
        self.assertEqual(timesheets_by_employee.get(self.part_time_employee2.id), 2)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee.id), 2)
        self.assertEqual(timesheets_by_employee.get(self.full_time_employee_2.id), 2)
        self.assertEqual(leave_task.effective_hours, 56)

    def test_timesheet_creation_and_deletion_for_calendar_update(self):
        attendance_ids_40h = [
            Command.create(
                {
                    "name": "Monday Morning",
                    "dayofweek": "0",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Monday Afternoon",
                    "dayofweek": "0",
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Tuesday Morning",
                    "dayofweek": "1",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Tuesday Afternoon",
                    "dayofweek": "1",
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Wednesday Morning",
                    "dayofweek": "2",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Wednesday Afternoon",
                    "dayofweek": "2",
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Thursday Morning",
                    "dayofweek": "3",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Thursday Afternoon",
                    "dayofweek": "3",
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Friday Morning",
                    "dayofweek": "4",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Friday Afternoon",
                    "dayofweek": "4",
                    "hour_from": 13,
                    "hour_to": 17,
                    "day_period": "afternoon",
                }
            ),
        ]
        attendance_ids_35h = [
            Command.create(
                {
                    "name": "Monday Morning",
                    "dayofweek": "0",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Monday Afternoon",
                    "dayofweek": "0",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Tuesday Morning",
                    "dayofweek": "1",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Tuesday Afternoon",
                    "dayofweek": "1",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Wednesday Morning",
                    "dayofweek": "2",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Wednesday Afternoon",
                    "dayofweek": "2",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Thursday Morning",
                    "dayofweek": "3",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Thursday Afternoon",
                    "dayofweek": "3",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                }
            ),
            Command.create(
                {
                    "name": "Friday Morning",
                    "dayofweek": "4",
                    "hour_from": 8,
                    "hour_to": 12,
                    "day_period": "morning",
                }
            ),
            Command.create(
                {
                    "name": "Friday Afternoon",
                    "dayofweek": "4",
                    "hour_from": 13,
                    "hour_to": 16,
                    "day_period": "afternoon",
                }
            ),
        ]
        calendar_40h, calendar_35h = self.env["resource.calendar"].create(
            [
                {
                    "name": "Calendar 40h",
                    "company_id": self.test_company.id,
                    "hours_per_day": 8,
                    "attendance_ids": attendance_ids_40h,
                },
                {
                    "name": "Calendar 35h",
                    "company_id": self.test_company.id,
                    "hours_per_day": 8,
                    "attendance_ids": attendance_ids_35h,
                },
            ]
        )
        gto_09_04, gto_09_11, gto_11_06, gto_11_13 = self.env[
            "resource.schedule.exception"
        ].create(
            [
                {
                    "name": "Global Time Off 4 Setpember",
                    "date_from": datetime(2023, 9, 4, 7, 0, 0, 0),
                    "date_to": datetime(2023, 9, 4, 18, 0, 0, 0),
                    "calendar_id": calendar_40h.id,
                },
                {
                    "name": "Global Time Off 11 Setpember",
                    "date_from": datetime(2023, 9, 11, 7, 0, 0, 0),
                    "date_to": datetime(2023, 9, 11, 18, 0, 0, 0),
                    "calendar_id": calendar_35h.id,
                },
                {
                    "name": "Global Time Off 6 November",
                    "date_from": datetime(2023, 11, 6, 7, 0, 0, 0),
                    "date_to": datetime(2023, 11, 6, 18, 0, 0, 0),
                    "calendar_id": calendar_40h.id,
                },
                {
                    "name": "Global Time Off 13 November",
                    "date_from": datetime(2023, 11, 13, 7, 0, 0, 0),
                    "date_to": datetime(2023, 11, 13, 18, 0, 0, 0),
                    "calendar_id": calendar_35h.id,
                },
            ]
        )

        with freeze_time("2023-08-10"):
            self.full_time_employee.resource_calendar_id = calendar_40h.id
        timesheets_employee_40h = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.full_time_employee.id)]
        )
        global_leaves_ids_40h = timesheets_employee_40h.global_leave_id
        self.assertEqual(len(global_leaves_ids_40h), 2)
        self.assertIn(gto_09_04, global_leaves_ids_40h)
        self.assertIn(gto_11_06, global_leaves_ids_40h)

        with freeze_time("2023-10-10"):
            self.full_time_employee.resource_calendar_id = calendar_35h.id
        timesheets_employee_35h = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.full_time_employee.id)]
        )
        global_leaves_ids_35h = timesheets_employee_35h.global_leave_id
        self.assertEqual(len(global_leaves_ids_35h), 2)
        self.assertIn(gto_09_04, global_leaves_ids_35h)
        self.assertIn(gto_11_13, global_leaves_ids_35h)
        self.assertNotIn(gto_09_11, global_leaves_ids_35h)

    def test_global_time_off_timesheet_creation_after_leave_refusal(self):
        test_user = (
            self.env["res.users"]
            .with_company(self.test_company)
            .create(
                {
                    "name": "Jonathan Doe",
                    "login": "jdoe@example.com",
                    "group_ids": self.env.ref("hr_timesheet.group_hr_timesheet_user"),
                }
            )
        )
        test_user.with_company(self.test_company).action_create_employee()
        test_user.employee_id.write(
            {
                "resource_calendar_id": self.test_company.resource_calendar_id.id,
            }
        )
        test_user.partner_id.write(
            {
                "email": "jdoe@example.com",
            }
        )

        today = datetime.today()
        next_monday = today.date() + timedelta(days=-today.weekday(), weeks=1)
        hr_leave_start_datetime = datetime(
            next_monday.year, next_monday.month, next_monday.day, 8, 0, 0
        )
        hr_leave_end_datetime = hr_leave_start_datetime + timedelta(days=4, hours=9)

        self.env = self.env(
            context=dict(self.env.context, allowed_company_ids=self.test_company.ids)
        )

        hr_leave_type_with_ts = self.env["hr.leave.type"].create(
            {
                "name": "Leave Type with timesheet generation",
                "requires_allocation": False,
            }
        )

        HrLeave = self.env["hr.leave"].with_context(
            mail_create_nolog=True, mail_notrack=True
        )
        holiday = HrLeave.with_user(test_user).create(
            {
                "name": "Leave 1",
                "employee_id": test_user.employee_id.id,
                "holiday_status_id": hr_leave_type_with_ts.id,
                "request_date_from": hr_leave_start_datetime,
                "request_date_to": hr_leave_end_datetime,
            }
        )
        holiday.sudo().action_approve()
        self.assertEqual(len(holiday.timesheet_ids), 5)

        global_leave_start_datetime = hr_leave_start_datetime + timedelta(
            days=2, hours=-3
        )
        global_leave_end_datetime = global_leave_start_datetime + timedelta(hours=12)

        global_time_off = self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": global_leave_start_datetime,
                "date_to": global_leave_end_datetime,
            }
        )
        gto_without_calendar = self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday without calendar",
                "date_from": global_leave_start_datetime + timedelta(days=1),
                "date_to": global_leave_end_datetime + timedelta(days=1),
            }
        )

        self.assertFalse(
            global_time_off.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )
        self.assertFalse(
            gto_without_calendar.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )

        holiday.sudo().action_refuse()
        self.assertFalse(holiday.timesheet_ids)

        self.assertTrue(
            global_time_off.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )
        self.assertTrue(
            gto_without_calendar.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )

        global_time_off.unlink()
        gto_without_calendar.unlink()

        holiday2 = HrLeave.with_user(test_user).create(
            {
                "name": "Leave 2",
                "employee_id": test_user.employee_id.id,
                "holiday_status_id": hr_leave_type_with_ts.id,
                "request_date_from": hr_leave_start_datetime,
                "request_date_to": hr_leave_end_datetime,
            }
        )
        holiday2.sudo().action_approve()

        global_time_off = self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": global_leave_start_datetime,
                "date_to": global_leave_end_datetime,
            }
        )
        gto_without_calendar = self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday without calendar",
                "date_from": global_leave_start_datetime + timedelta(days=1),
                "date_to": global_leave_end_datetime + timedelta(days=1),
            }
        )

        self.assertFalse(
            global_time_off.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )
        self.assertFalse(
            gto_without_calendar.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )

        holiday2.with_user(test_user)._action_user_cancel("User cancelled leave")
        self.assertFalse(holiday2.timesheet_ids)

        self.assertTrue(
            global_time_off.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )
        self.assertTrue(
            gto_without_calendar.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )

        holiday3 = HrLeave.with_user(test_user).create(
            {
                "name": "Leave 3",
                "employee_id": test_user.employee_id.id,
                "holiday_status_id": hr_leave_type_with_ts.id,
                "request_date_from": hr_leave_start_datetime,
                "request_date_to": hr_leave_end_datetime,
            }
        )
        holiday3.sudo().action_approve()

        self.assertEqual(len(holiday3.timesheet_ids), 3)
        global_time_off.unlink()
        self.assertEqual(len(holiday3.timesheet_ids), 4)
        gto_without_calendar.calendar_id = self.part_time_calendar
        self.assertFalse(
            gto_without_calendar.timesheet_ids.filtered(
                lambda r: r.employee_id == test_user.employee_id
            )
        )
        self.assertEqual(len(holiday3.timesheet_ids), 5)
        self.assertEqual(sum(holiday3.timesheet_ids.mapped("unit_amount")), 40)

    def test_unlink_timesheet_with_global_time_off(self):
        leave_start = datetime(2025, 1, 1, 7, 0)
        leave_end = datetime(2025, 1, 1, 18, 0)

        global_time_off = self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "calendar_id": self.test_company.resource_calendar_id.id,
                "date_from": leave_start,
                "date_to": leave_end,
            }
        )

        timesheet = self.env["account.analytic.line"].search(
            [
                ("global_leave_id", "=", global_time_off.id),
                ("employee_id", "=", self.full_time_employee.id),
            ]
        )

        with self.assertRaises(UserError):
            timesheet.unlink()

    def test_timesheet_generation_on_public_holiday_creation_with_global_working_schedule(
        self,
    ):
        self.part_time_calendar.company_id = False
        self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "date_from": datetime(2021, 1, 4, 0, 0, 0),
                "date_to": datetime(2021, 1, 4, 23, 59, 59),
            }
        )
        timesheet_count = self.env["account.analytic.line"].search_count(
            [("employee_id", "=", self.part_time_employee.id)]
        )
        self.assertEqual(
            timesheet_count,
            1,
            "A timesheet should have been generated for the employee with a global working "
            "schedule when a new public holiday is created",
        )

    def test_timesheet_generation_on_public_holiday_creation_with_flexible_hours(self):

        self.flexible_calendar = self.env["resource.calendar"].create(
            {
                "name": "Flexible Calendar",
                "hours_per_day": 7.0,
                "full_time_required_hours": 7.0,
                "flexible_hours": True,
            }
        )

        self.flexible_employee = self.env["hr.employee"].create(
            {
                "name": "Flexible",
                "company_id": self.test_company.id,
                "resource_calendar_id": self.flexible_calendar.id,
            }
        )

        self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "date_from": datetime(2021, 1, 4, 0, 0, 0),
                "date_to": datetime(2021, 1, 4, 23, 59, 59),
            }
        )
        timesheet = self.env["account.analytic.line"].search(
            [("employee_id", "=", self.flexible_employee.id)]
        )
        self.assertEqual(timesheet.unit_amount, self.flexible_calendar.hours_per_day)
