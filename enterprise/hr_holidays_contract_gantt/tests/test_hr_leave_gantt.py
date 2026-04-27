# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.addons.hr_holidays_contract.tests.common import TestHolidayContract


class TestHrLeaveGantt(TestHolidayContract):

    def test_gantt_view_without_schedule(self):
        """
        Test that the Time Off Gantt view works correctly even
        when an employee contract has no working schedule set.
        """
        # Remove the working schedule (resource calendar) from the employee's contract
        self.contract_cdi.write({
            'date_start': datetime.strptime('2025-01-01', '%Y-%m-%d').date(),
            'date_end': datetime.strptime('2025-12-31', '%Y-%m-%d').date(),
            'resource_calendar_id': None
        })

        # Create a time off for the employee
        start = datetime.strptime('2025-11-11 07:00:00', '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime('2025-11-11 18:00:00', '%Y-%m-%d %H:%M:%S')
        self.create_leave(start, end, name="Doctor Appointment", employee_id=self.jules_emp.id)

        # Get the Gantt overview data for employees's time off data
        start_date = '2025-11-01 00:00:00'
        stop_date = '2025-11-30 00:00:00'
        gantt_domain = [('employee_id.active', '=', True)]
        gantt_data = self.env["hr.leave.report.calendar"].get_gantt_data(
            gantt_domain,
            ["employee_id"],
            {},
            unavailability_fields=["employee_id"],
            start_date=start_date,
            stop_date=stop_date,
            scale="day",
        )
        group_employee_ids = [group['employee_id'][0] for group in gantt_data['groups']]
        self.assertIn(self.jules_emp.id, group_employee_ids, "The employee should be in the gantt data groups.")
