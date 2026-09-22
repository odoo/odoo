from datetime import datetime

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestDashboard(TestHrHolidaysCommon):
    def test_dashboard_special_days(self):
        self.uid = self.user_hrmanager.id
        employee = self.env.user.employee_id
        other_calendar = (
            self.env["resource.calendar"]
            .sudo()
            .create(
                {
                    "name": "Other calendar",
                }
            )
        )

        mandatory_day_vals = [
            {
                "name": "Super Event (employee schedule)",
                "company_id": employee.company_id.id,
                "start_date": datetime(2021, 6, 12),
                "end_date": datetime(2021, 6, 12),
                "resource_calendar_id": employee.resource_calendar_id.id,
            },
            {
                "name": "Super Event (no schedule)",
                "company_id": employee.company_id.id,
                "start_date": datetime(2021, 6, 12),
                "end_date": datetime(2021, 6, 12),
            },
            {
                "name": "Super Event (other schedule)",
                "company_id": employee.company_id.id,
                "start_date": datetime(2021, 6, 12),
                "end_date": datetime(2021, 6, 12),
                "resource_calendar_id": other_calendar.id,
            },
        ]
        self.env["hr.leave.mandatory.day"].create(mandatory_day_vals)

        public_holiday_vals = [
            {
                "name": "Public holiday (employee schedule)",
                "date_from": "2021-06-15 06:00:00",
                "date_to": "2021-06-15 15:00:00",
                "calendar_id": employee.resource_calendar_id.id,
            },
            {
                "name": "Public holiday (no schedule)",
                "date_from": "2021-06-16 06:00:00",
                "date_to": "2021-06-16 15:00:00",
            },
            {
                "name": "Public holiday (other schedule)",
                "date_from": "2021-06-17 06:00:00",
                "date_to": "2021-06-17 15:00:00",
                "calendar_id": other_calendar.id,
            },
        ]
        self.env["resource.schedule.exception"].create(public_holiday_vals)

        dashboard_data = self.env["hr.employee"].get_special_days_data(
            "2021-06-01", "2021-07-01"
        )

        self.assertEqual(
            {d["title"] for d in dashboard_data["mandatoryDays"]},
            {"Super Event (employee schedule)", "Super Event (no schedule)"},
        )
        self.assertEqual(
            {d["title"] for d in dashboard_data["bankHolidays"]},
            {"Public holiday (employee schedule)", "Public holiday (no schedule)"},
        )

    def test_special_days_answer_for_the_employee_company(self):
        """The side panel must answer for the employee, like the day grid does.

        `hr.employee._get_unusual_days` already hands the employee's company
        down to the calendar, so the grid greys out that company's days and no
        other. The side panel was reading every company the user had switched
        on, so the two halves of the same screen disagreed about the same day
        and a holiday of a sister company showed up on someone else's calendar.
        """
        other_company = self.external_company
        self.env["hr.leave.mandatory.day"].create(
            [
                {
                    "name": "Mandatory day here",
                    "company_id": self.company.id,
                    "start_date": datetime(2021, 6, 12),
                    "end_date": datetime(2021, 6, 12),
                },
                {
                    "name": "Mandatory day next door",
                    "company_id": other_company.id,
                    "start_date": datetime(2021, 6, 12),
                    "end_date": datetime(2021, 6, 12),
                },
            ]
        )
        # `resource.schedule.exception.company_id` is a stored compute that
        # falls back to the active company, so a public holiday belongs to
        # whoever was working in it -- which is how each company's holidays get
        # created in the first place.
        self.env["resource.schedule.exception"].with_company(self.company).create(
            {
                "name": "Public holiday here",
                "date_from": "2021-06-16 06:00:00",
                "date_to": "2021-06-16 15:00:00",
            }
        )
        self.env["resource.schedule.exception"].with_company(other_company).create(
            {
                "name": "Public holiday next door",
                "date_from": "2021-06-17 06:00:00",
                "date_to": "2021-06-17 15:00:00",
            }
        )

        dashboard_data = (
            self.env["hr.employee"]
            .with_context(
                employee_id=self.employee_emp_id,
                allowed_company_ids=[self.company.id, other_company.id],
            )
            .get_special_days_data("2021-06-01", "2021-07-01")
        )

        self.assertEqual(
            {d["title"] for d in dashboard_data["mandatoryDays"]},
            {"Mandatory day here"},
            "a mandatory day of another company is not this employee's",
        )
        self.assertEqual(
            {d["title"] for d in dashboard_data["bankHolidays"]},
            {"Public holiday here"},
            "a public holiday of another company is not this employee's",
        )
