from datetime import datetime

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestDashboard(TestHrHolidaysCommon):
    def test_dashboard_special_days(self):
        self.uid = self.user_hrmanager.id
        employee = self.env.user.employee_id
        other_calendar = self.env['resource.calendar'].sudo().create({
            'name': 'Other calendar',
        })

        mandatory_day_vals = [
            {
                'name': 'Super Event (employee schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
                'resource_calendar_id': employee.resource_calendar_id.id,
            },
            {
                'name': 'Super Event (no schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
            },
            {
                'name': 'Super Event (other schedule)',
                'company_id': employee.company_id.id,
                'start_date': datetime(2021, 6, 12),
                'end_date': datetime(2021, 6, 12),
                'resource_calendar_id': other_calendar.id,
            }
        ]
        self.env['hr.leave.mandatory.day'].create(mandatory_day_vals)

        public_holiday_vals = [
            {
                'name': 'Public holiday (employee schedule)',
                'date_from': "2021-06-15 06:00:00",
                'date_to': "2021-06-15 15:00:00",
                'calendar_id': employee.resource_calendar_id.id,
            },
            {
                'name': 'Public holiday (no schedule)',
                'date_from': "2021-06-16 06:00:00",
                'date_to': "2021-06-16 15:00:00",
            },
            {
                'name': 'Public holiday (other schedule)',
                'date_from': "2021-06-17 06:00:00",
                'date_to': "2021-06-17 15:00:00",
                'calendar_id': other_calendar.id,
            },
        ]
        self.env['resource.calendar.leaves'].create(public_holiday_vals)

        dashboard_data = self.env['hr.employee'].get_special_days_data("2021-06-01", "2021-07-01")

        self.assertEqual({d["title"] for d in dashboard_data["mandatoryDays"]}, {'Super Event (employee schedule)', 'Super Event (no schedule)'})
        self.assertEqual({d["title"] for d in dashboard_data["bankHolidays"]}, {'Public holiday (employee schedule)', 'Public holiday (no schedule)'})
