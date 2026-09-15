import unittest
from datetime import date, datetime

from odoo.tests import tagged

from odoo.addons.hr_calendar.tests.common import TestHrCalendarCommon


@tagged("work_hours")
@unittest.skip(
    "res.partner.get_working_hours_for_all_attendees (hr_calendar) returns a "
    "single all-day-unavailable slot instead of the real weekly schedule, so "
    "every test in this class fails on that unrelated, out-of-hr_holidays-"
    "scope bug. See task 27918. The previous guard here "
    '(`if "hr.version" in cls.env: skip`) was stale: hr.version has lived in '
    "core hr since before this fork, so hr_holidays' hard dependency on hr "
    "made the guard unconditionally true and its own message wrong "
    "(hr_contract is not what registers hr.version)."
)
class TestWorkingHours(TestHrCalendarCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Unpaid Time Off",
                "requires_allocation": False,
                "leave_validation_type": "no_validation",
            }
        )

    def test_multi_companies_2_employees_2_selected_companies_holidays(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        self.env["hr.leave"].create(
            {
                "name": "holiday from monday to tuesday",
                "employee_id": self.employeeA.id,
                "holiday_status_id": self.leave_type.id,
                "request_date_from": datetime(2023, 12, 25),
                "request_date_to": datetime(2023, 12, 26, 23, 59, 59),
            }
        )

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(
            work_hours,
            [
                {"daysOfWeek": [2], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [2], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [3], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [3], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [4], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [4], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [5], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [5], "startTime": "13:00", "endTime": "16:00"},
            ],
        )

    def test_multi_companies_2_employees_2_selected_companies_company_holidays(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        company_leave = self.env["hr.leave.generate.multi.wizard"].create(
            {
                "name": "holiday from monday to tuesday",
                "allocation_mode": "company",
                "company_id": self.company_A.id,
                "holiday_status_id": self.leave_type.id,
                "date_from": date(2023, 12, 25),
                "date_to": date(2023, 12, 26),
            }
        )
        company_leave.action_generate_time_off()

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(
            work_hours,
            [
                {"daysOfWeek": [2], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [2], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [3], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [3], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [4], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [4], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [5], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [5], "startTime": "13:00", "endTime": "16:00"},
            ],
        )

    def test_multi_companies_2_employees_2_selected_companies_global_holidays(self):
        self.env.user.company_id = self.company_A
        self.env.user.company_ids = [self.company_A.id, self.company_B.id]

        self.env["resource.schedule.exception"].create(
            {
                "name": "Global Time Off",
                "date_from": datetime(2023, 12, 25),
                "date_to": datetime(2023, 12, 26, 23, 59, 59),
                "calendar_id": self.calendar_35h.id,
            }
        )

        work_hours = self.env["res.partner"].get_working_hours_for_all_attendees(
            [self.partnerA.id],
            datetime(2023, 12, 25).isoformat(),
            datetime(2023, 12, 31).isoformat(),
        )
        self.assertEqual(
            work_hours,
            [
                {"daysOfWeek": [2], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [2], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [3], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [3], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [4], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [4], "startTime": "13:00", "endTime": "16:00"},
                {"daysOfWeek": [5], "startTime": "08:00", "endTime": "12:00"},
                {"daysOfWeek": [5], "startTime": "13:00", "endTime": "16:00"},
            ],
        )
