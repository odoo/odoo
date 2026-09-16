from datetime import date, datetime, timedelta

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("global_leaves")
class TestGlobalLeaves(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_1 = cls.env["resource.calendar"].create(
            {
                "name": "Classic 40h/week",
                "tz": "UTC",
                "hours_per_day": 8.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Monday Morning",
                            "dayofweek": "0",
                            "hour_from": 8,
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
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Morning",
                            "dayofweek": "1",
                            "hour_from": 8,
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
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Morning",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Lunch",
                            "dayofweek": "2",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Afternoon",
                            "dayofweek": "2",
                            "hour_from": 13,
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Morning",
                            "dayofweek": "3",
                            "hour_from": 8,
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
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Morning",
                            "dayofweek": "4",
                            "hour_from": 8,
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
                            "hour_to": 17,
                            "day_period": "afternoon",
                        },
                    ),
                ],
            }
        )

        cls.calendar_2 = cls.env["resource.calendar"].create(
            {
                "name": "Classic 20h/week",
                "tz": "UTC",
                "hours_per_day": 4.0,
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Monday Morning",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Morning",
                            "dayofweek": "1",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Morning",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Morning",
                            "dayofweek": "3",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Morning",
                            "dayofweek": "4",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                ],
            }
        )

        cls.global_leave = cls.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off",
                "local_date_from": date(2022, 3, 7),
                "local_date_to": date(2022, 3, 7),
            }
        )

        cls.calendar_leave = cls.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off",
                "local_date_from": date(2022, 3, 8),
                "local_date_to": date(2022, 3, 8),
                "calendar_id": cls.calendar_1.id,
            }
        )

    def test_calendar_time_off_count_includes_company_wide_holidays(self):
        (self.calendar_1 | self.calendar_2).invalidate_recordset(
            ["associated_leaves_count"]
        )
        self.assertEqual(self.calendar_1.associated_leaves_count, 2)
        self.assertEqual(self.calendar_2.associated_leaves_count, 1)

    def test_leave_on_global_leave(self):
        with self.assertRaises(ValidationError):
            self.env["resource.schedule.exception"].create(
                {
                    "name": "Wrong Time Off",
                    "local_date_from": date(2022, 3, 7),
                    "local_date_to": date(2022, 3, 7),
                    "calendar_id": self.calendar_1.id,
                }
            )

        with self.assertRaises(ValidationError):
            self.env["resource.schedule.exception"].create(
                {
                    "name": "Wrong Time Off",
                    "local_date_from": date(2022, 3, 7),
                    "local_date_to": date(2022, 3, 7),
                }
            )

    def test_leave_on_calendar_leave(self):
        self.env["resource.schedule.exception"].create(
            {
                "name": "Correct Time Off",
                "local_date_from": date(2022, 3, 8),
                "local_date_to": date(2022, 3, 8),
                "calendar_id": self.calendar_2.id,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["resource.schedule.exception"].create(
                {
                    "name": "Wrong Time Off",
                    "local_date_from": date(2022, 3, 8),
                    "local_date_to": date(2022, 3, 8),
                }
            )

        with self.assertRaises(ValidationError):
            self.env["resource.schedule.exception"].create(
                {
                    "name": "Wrong Time Off",
                    "local_date_from": date(2022, 3, 8),
                    "local_date_to": date(2022, 3, 8),
                    "calendar_id": self.calendar_1.id,
                }
            )

    @freeze_time("2023-05-12")
    def test_global_leave_timezone(self):
        calendar_asia = self.env["resource.calendar"].create(
            {
                "name": "Asia calendar",
                "tz": "Asia/Kolkata",
                "hours_per_day": 8.0,
                "attendance_ids": [],
            }
        )
        self.env.user.tz = "Europe/Brussels"
        global_leave = (
            self.env["resource.schedule.exception"]
            .with_user(self.env.user)
            .create(
                {
                    "name": "Public holiday",
                    "local_date_from": "2023-05-15",
                    "local_hour_from": 8.0,
                    "local_date_to": "2023-05-15",
                    "local_hour_to": 17.0,
                    "calendar_id": calendar_asia.id,
                }
            )
        )
        self.assertEqual(global_leave.tz, "Asia/Kolkata")
        self.assertEqual(global_leave.date_from, datetime(2023, 5, 15, 2, 30))
        self.assertEqual(global_leave.date_to, datetime(2023, 5, 15, 11, 30))

        self.assertEqual(global_leave.local_hour_from, 8.0)
        self.assertEqual(global_leave.local_hour_to, 17.0)

    @freeze_time("2023-05-12")
    def test_a_global_leave_keeps_the_instants_a_caller_writes(self):
        calendar_asia = self.env["resource.calendar"].create(
            {
                "name": "Asia calendar",
                "tz": "Asia/Kolkata",
                "attendance_ids": [],
            }
        )
        self.env.user.tz = "Europe/Brussels"
        global_leave = self.env["resource.schedule.exception"].create(
            {
                "name": "Public holiday",
                "date_from": "2023-05-15 06:00:00",
                "date_to": "2023-05-15 15:00:00",
                "calendar_id": calendar_asia.id,
            }
        )
        self.assertEqual(global_leave.date_from, datetime(2023, 5, 15, 6, 0))
        self.assertEqual(global_leave.date_to, datetime(2023, 5, 15, 15, 0))
        self.assertEqual(global_leave.local_hour_from, 11.5)

    def test_global_leave_working_schedule_without_company(self):
        calendar_no_company = self.env["resource.calendar"].create(
            {
                "name": "Schedule without company",
                "company_id": False,
            }
        )
        self.employee_emp.resource_calendar_id = calendar_no_company

        self.env["resource.schedule.exception"].create(
            {
                "name": "Public Holiday",
                "date_from": datetime(2024, 1, 3, 0, 0),
                "date_to": datetime(2024, 1, 3, 23, 59),
                "calendar_id": calendar_no_company.id,
                "company_id": self.employee_emp.company_id.id,
            }
        )
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": False,
            }
        )
        leave = self.env["hr.leave"].create(
            {
                "name": "Time Off",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": date(2024, 1, 2),
                "request_date_to": date(2024, 1, 4),
            }
        )

        self.assertEqual(
            leave.number_of_days, 2, "Public holiday duration should not be included"
        )

    def test_global_leave_number_of_days_with_new(self):
        global_leave = self.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off",
                "date_from": datetime(2024, 1, 3, 6, 0, 0),
                "date_to": datetime(2024, 1, 3, 19, 0, 0),
                "calendar_id": self.calendar_1.id,
            }
        )
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": False,
            }
        )
        self.employee_emp.resource_calendar_id = self.calendar_1.id

        leave = self.env["hr.leave"].create(
            {
                "name": "Test new leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": global_leave.date_from,
                "request_date_to": global_leave.date_to,
            }
        )
        self.assertEqual(leave.number_of_days, 0, "It is a global leave")

        leave = self.env["hr.leave"].new(
            {
                "name": "Test new leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": global_leave.date_from,
                "request_date_to": global_leave.date_to,
            }
        )
        self.assertEqual(leave.number_of_days, 0, "It is a global leave")

        leave = self.env["hr.leave"].new(
            {
                "name": "Test new leave",
                "employee_id": self.employee_emp.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": global_leave.date_from - timedelta(days=1),
                "request_date_to": global_leave.date_to + timedelta(days=1),
            }
        )
        self.assertEqual(leave.number_of_days, 2, "There is a global leave")

    @freeze_time("2024-12-01")
    def test_global_leave_keeps_employee_resource_leave(self):
        employee = self.employee_emp
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "request_unit": "hour",
                "leave_validation_type": "both",
            }
        )
        self.env["hr.leave.allocation"].create(
            {
                "name": "20 days allocation",
                "holiday_status_id": leave_type.id,
                "number_of_days": 20,
                "employee_id": employee.id,
                "state": "confirm",
                "date_from": date(2024, 12, 1),
                "date_to": date(2024, 12, 30),
            }
        ).action_approve()

        partially_covered_leave = self.env["hr.leave"].create(
            {
                "name": "Holiday 1 week",
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": datetime(2024, 12, 3, 7, 0),
                "request_date_to": datetime(2024, 12, 5, 18, 0),
            }
        )
        partially_covered_leave.action_approve()

        self.env["resource.schedule.exception"].with_user(self.env.user).create(
            {
                "name": "Public holiday",
                "date_from": "2024-12-04 06:00:00",
                "date_to": "2024-12-04 23:00:00",
                "calendar_id": self.calendar_1.id,
            }
        )

        resource_leaves = self.env["resource.schedule.exception"].search(
            [("holiday_id", "=", partially_covered_leave.id)]
        )
        self.assertTrue(
            resource_leaves,
            "Resource leaves linked to the employee leave should exist.",
        )

    @freeze_time("2025-05-11")
    def test_employee_leave_with_global_leave(self):
        user_david = mail_new_test_user(
            self.env, login="david", groups="base.group_user"
        )
        user_timeoff_officer_david = mail_new_test_user(
            self.env, login="timeoff_officer", groups="base.group_user"
        )

        employee_david = self.env["hr.employee"].create(
            {
                "name": "David Employee",
                "user_id": user_david.id,
                "leave_manager_id": user_timeoff_officer_david.id,
                "parent_id": self.employee_hruser.id,
                "department_id": self.rd_dept.id,
                "resource_calendar_id": self.calendar_1.id,
            }
        )
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Sick Time Off",
                "requires_allocation": False,
                "leave_validation_type": "both",
            }
        )

        employee_leave = self.env["hr.leave"].create(
            {
                "name": "Holiday 5 days",
                "employee_id": employee_david.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": datetime(2025, 5, 12),
                "request_date_to": datetime(2025, 5, 16),
            }
        )

        self.env["resource.schedule.exception"].with_user(self.user_hrmanager).create(
            {
                "name": "Public holiday day 1",
                "date_from": datetime(2025, 5, 13),
                "date_to": datetime(2025, 5, 13, 23, 59),
                "calendar_id": employee_david.resource_calendar_id.id,
            }
        )

        self.assertEqual(
            employee_leave.number_of_days,
            4,
            "Leave duration should be reduced because of public holiday day 1",
        )

        employee_leave.with_user(user_timeoff_officer_david).action_approve()
        self.env["resource.schedule.exception"].with_user(self.user_hrmanager).create(
            {
                "name": "Public holiday day 2",
                "date_from": datetime(2025, 5, 14),
                "date_to": datetime(2025, 5, 14, 23, 59),
                "calendar_id": employee_david.resource_calendar_id.id,
            }
        )
        self.assertEqual(
            employee_leave.number_of_days,
            3,
            "Leave duration should be reduced because of public holiday day 2",
        )

        employee_leave.with_user(self.user_hruser).action_approve()
        self.env["resource.schedule.exception"].with_user(self.user_hrmanager).create(
            {
                "name": "Public holiday day 3",
                "date_from": datetime(2025, 5, 15),
                "date_to": datetime(2025, 5, 15, 23, 59),
                "calendar_id": employee_david.resource_calendar_id.id,
            }
        )
        self.assertEqual(
            employee_leave.number_of_days,
            2,
            "Leave duration should be reduced because of public holiday day 3",
        )

    def test_multi_day_public_holidays_for_flexible_schedule(self):
        flex_cal = self.env["resource.calendar"].create(
            {
                "name": "Flexible",
                "tz": "UTC",
                "flexible_hours": True,
                "hours_per_day": 8.0,
            }
        )

        self.env["resource.schedule.exception"].create(
            {
                "name": "3 day holiday",
                "calendar_id": flex_cal.id,
                "date_from": datetime(2024, 3, 5),
                "date_to": date(2024, 3, 7),
            }
        )

        start = datetime(2024, 3, 4)
        end = datetime(2024, 3, 10)

        flex_days = flex_cal._get_unusual_days(start, end)

        expected = {
            "2024-03-04": False,
            "2024-03-05": True,
            "2024-03-06": True,
            "2024-03-07": True,
            "2024-03-08": False,
            "2024-03-09": False,
            "2024-03-10": False,
        }
        for day, value in expected.items():
            self.assertEqual(
                flex_days.get(day),
                value,
                f"Day {day} should be {'unusual' if value else 'normal'}",
            )

    def test_public_holidays_for_consecutive_allocations(self):
        employee = self.employee_emp
        leave_type = self.env["hr.leave.type"].create(
            {
                "name": "Paid Time Off",
                "requires_allocation": "yes",
            }
        )
        self.env["hr.leave.allocation"].create(
            [
                {
                    "name": "2025 allocation",
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 20,
                    "employee_id": employee.id,
                    "state": "confirm",
                    "date_from": date(2025, 1, 1),
                    "date_to": date(2025, 12, 31),
                },
                {
                    "name": "2026 allocation",
                    "holiday_status_id": leave_type.id,
                    "number_of_days": 20,
                    "employee_id": employee.id,
                    "state": "confirm",
                    "date_from": date(2026, 1, 1),
                    "date_to": date(2026, 12, 31),
                },
            ]
        ).action_approve()

        leave = self.env["hr.leave"].create(
            {
                "name": "Holiday 1 week",
                "employee_id": employee.id,
                "holiday_status_id": leave_type.id,
                "request_date_from": datetime(2025, 12, 8, 7, 0),
                "request_date_to": datetime(2026, 1, 3, 18, 0),
            }
        )
        leave.action_approve()

        self.assertEqual(leave.number_of_days, 20, "Number of days should be 20")

        public_holiday = self.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off",
                "date_from": datetime(2025, 12, 31, 23, 0, 0),
                "date_to": datetime(2026, 1, 1, 22, 59, 59),
            }
        )

        self.assertTrue(public_holiday)
        self.assertEqual(
            leave.number_of_days,
            19,
            "Number of days should be 19 as one day has been granted back to the"
            "the employee for the public holiday",
        )
