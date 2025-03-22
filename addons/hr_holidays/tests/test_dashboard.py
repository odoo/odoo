from datetime import date, datetime
from freezegun import freeze_time

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


class TestDashboard(TestHrHolidaysCommon):
    def test_dashboard_special_days(self):
        self.env.user = self.user_hrmanager
        employee = self.env.user.employee_id
        other_calendar = employee.company_id.resource_calendar_ids[1]

        stress_day_vals = [
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
        self.env['hr.leave.stress.day'].create(stress_day_vals)

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

        dashboard_data = self.env['hr.employee'].get_special_days_data("2021/06/01", "2021/07/01")

        self.assertEqual({d["title"] for d in dashboard_data["stressDays"]}, {'Super Event (employee schedule)', 'Super Event (no schedule)'})
        self.assertEqual({d["title"] for d in dashboard_data["bankHolidays"]}, {'Public holiday (employee schedule)', 'Public holiday (no schedule)'})

    def test_dashboard_max_near_accrual_validity_end(self):
        emp_id = self.employee_emp_id
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Test Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'no',
            'leave_validation_type': 'both',
            'responsible_id': self.user_hrmanager_id,
        })
        self.env['hr.leave.allocation'].create([{
            'employee_id': emp_id,
            'name': '10 days allocation',
            'holiday_status_id': leave_type.id,
            'number_of_days': 10,
            'date_from': date(2024, 1, 1),
            'date_to': date(2024, 12, 30),
        }, {
            'employee_id': emp_id,
            'name': '2 days allocation starting later',
            'holiday_status_id': leave_type.id,
            'number_of_days': 2,
            'date_from': date(2024, 2, 1),
            'date_to': date(2024, 12, 30),
        }])

        with freeze_time('2024-12-27'):
            employee_max_leaves = leave_type.get_employees_days([emp_id])[emp_id][leave_type.id]['max_leaves']
            self.assertEqual(employee_max_leaves, 12, "All 12 leaves should be seen from the dashboard")

