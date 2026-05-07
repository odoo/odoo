from freezegun import freeze_time

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


@tagged('-at_install', 'post_install', 'holidays_attendance')
class TestLeaveAttendanceReport(TestHrHolidaysCommon):

    @freeze_time('2026-02-28')
    def test_overlap_leave_and_public_holiday(self):
        self.employee_emp.contract_date_start = "2026-02-01"
        self.env['resource.calendar.leaves'].create({
            'name': 'Some Public Holiday',
            'calendar_id': self.employee_emp.resource_calendar_id.id,
            'date_from': '2026-02-10 00:00:00',
            'date_to': '2026-02-10 18:00:00',
            'resource_id': False
        })
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Ignore Public Holiday Leave',
            'requires_allocation': False,
            'company_id': self.company.id,
            'include_public_holidays_in_duration': True,
        })
        leave = self.env['hr.leave'].create({
            'name': 'Some leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': leave_type.id,
            'request_date_from': "2026-02-09",
            'request_date_to': "2026-02-11",
        })
        leave.action_approve()
        non_overlap_days = (self.env["hr.leave.attendance.report"].search(
            ['&', '|', ('date', '=', '2026-02-09'), ('date', '=', '2026-02-11'), ('employee_id', '=', self.employee_emp.id)]))
        self.assertRecordValues(non_overlap_days, [{
            'expected_hours': 8.0,
            'leave_hours': 8.0,
            'difference_hours': 0.0,
        } for _ in range(2)])
