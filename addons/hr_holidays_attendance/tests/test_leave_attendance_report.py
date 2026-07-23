from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import fields
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
        work_entry_type = self.env['hr.work.entry.type'].create({
            'code': 'LEAVE',
            'name': 'Ignore Public Holiday Leave',
            'count_as': 'absence',
            'requires_allocation': False,
            'include_public_holidays_in_duration': True,
        })
        leave = self.env['hr.leave'].create({
            'name': 'Some leave',
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': work_entry_type.id,
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

    def test_report_all_branches(self):
        """Pin the business result while the SQL implementation stays free to change."""
        employee = self.employee_emp
        company = self.company
        calendar = employee.resource_calendar_id
        Report = self.env['hr.leave.attendance.report']
        today = fields.Date.today()
        # Use a Monday well inside the rolling report window, away from its edges.
        monday = today - timedelta(days=today.weekday() + 7 * 8)

        def day(week, weekday=0):
            return monday + timedelta(days=7 * week + weekday)

        def at(date, hour):
            return datetime(date.year, date.month, date.day, hour)

        def closure(date, calendar_id):
            self.env['resource.calendar.leaves'].create({
                'name': 'Closure',
                'calendar_id': calendar_id,
                'company_id': company.id,
                'date_from': at(date, 6),
                'date_to': at(date, 18),
                'resource_id': False,
            })

        def approve_leave(work_entry_type, date_from, date_to):
            self.env['hr.leave'].create({
                'name': 'Leave',
                'employee_id': employee.id,
                'work_entry_type_id': work_entry_type.id,
                'request_date_from': date_from,
                'request_date_to': date_to,
            }).action_approve()

        def row(date):
            return Report.search([
                ('employee_id', '=', employee.id),
                ('date', '=', date),
            ])

        leave_type_excl = self.env['hr.work.entry.type'].create({
            'name': 'Leave excluding public holidays',
            'code': 'LEAVE_EXCL',
            'count_as': 'absence',
            'requires_allocation': False,
            'include_public_holidays_in_duration': False,
        })
        leave_type_incl = self.env['hr.work.entry.type'].create({
            'name': 'Leave including public holidays',
            'code': 'LEAVE_INCL',
            'count_as': 'absence',
            'requires_allocation': False,
            'include_public_holidays_in_duration': True,
        })

        # The contract starts before the fixture and ends during its last week.
        employee.contract_date_start = monday - timedelta(days=14)
        employee.contract_date_end = day(5, 2)

        attendances = self.env['hr.attendance'].create([
            {
                'employee_id': employee.id,
                'check_in': at(day(0, 0), 12),
                'check_out': at(day(0, 0), 17),
            },
            {
                'employee_id': employee.id,
                'check_in': at(day(0, 1), 12),
                'check_out': at(day(0, 1), 18),
            },
            {
                'employee_id': employee.id,
                'check_in': at(day(0, 2), 12),
                'check_out': at(day(0, 2), 20),
            },
        ])
        worked = {
            weekday: round(attendance.worked_hours, 2)
            for weekday, attendance in zip((0, 1, 2), attendances)
        }
        closure(day(0, 4), calendar.id)

        # Excluding a Tuesday closure leaves two chargeable days.
        closure(day(1, 1), calendar.id)
        approve_leave(leave_type_excl, day(1, 0), day(1, 2))

        # Including it keeps three days in the leave-hour denominator, even
        # though the closure itself is never a row in the report.
        closure(day(2, 1), calendar.id)
        approve_leave(leave_type_incl, day(2, 0), day(2, 2))

        # A calendar-less closure applies company-wide.
        closure(day(3, 0), False)

        # The report is an SQL view, so flush stored attendance hours first.
        self.env.flush_all()

        for weekday in (0, 1, 2):
            self.assertRecordValues(row(day(0, weekday)), [{
                'worked_hours': worked[weekday],
                'expected_hours': 8.0,
                'leave_hours': 0.0,
                'difference_hours': round(worked[weekday] - 8.0, 2),
            }])
        self.assertRecordValues(row(day(0, 3)), [{
            'worked_hours': 0.0,
            'expected_hours': 8.0,
            'leave_hours': 0.0,
            'difference_hours': -8.0,
        }])

        self.assertFalse(row(day(0, 4)), "public holiday -> no row")
        self.assertFalse(row(day(0, 5)), "Saturday -> no row")
        self.assertFalse(row(day(0, 6)), "Sunday -> no row")
        self.assertFalse(row(day(3, 0)), "company-wide closure -> no row")

        for date in (day(1, 0), day(1, 2), day(2, 0), day(2, 2)):
            self.assertRecordValues(row(date), [{
                'worked_hours': 0.0,
                'expected_hours': 8.0,
                'leave_hours': 8.0,
                'difference_hours': 0.0,
            }])
        self.assertFalse(row(day(1, 1)), "public holiday inside leave -> no row")
        self.assertFalse(row(day(2, 1)), "public holiday inside leave -> no row")

        self.assertFalse(
            row(monday - timedelta(days=21)),
            "working day before contract start -> no row",
        )
        self.assertRecordValues(row(day(5, 2)), [{
            'worked_hours': 0.0,
            'expected_hours': 8.0,
            'leave_hours': 0.0,
            'difference_hours': -8.0,
        }])
        self.assertFalse(row(day(5, 3)), "working day after contract end -> no row")
