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

    def test_report_all_branches(self):
        """ Characterisation test for the report's SQL view.

            One fixture exercises every branch of the view: attendance worked
            below / equal to / above the expected hours, leave pro-ration with
            both `include_public_holidays_in_duration` values, a public
            holiday, a company-wide closure (calendar-less leave), weekends
            and contract bounds.  The resulting values are pinned below.

            Not covered here (no stable fixture API): an employee with several
            `hr_version` rows; that branch is checked by the production
            old-vs-new comparison instead.
        """
        emp = self.employee_emp
        company = self.company
        calendar = emp.resource_calendar_id
        Report = self.env['hr.leave.attendance.report']

        today = fields.Date.today()
        # Monday eight weeks before this week: comfortably inside the report's
        # ~13-month window and clear of both its edges.
        monday = today - timedelta(days=today.weekday() + 7 * 8)

        def day(week, weekday=0):
            return monday + timedelta(days=7 * week + weekday)

        def at(d, hour):
            return datetime(d.year, d.month, d.day, hour)

        def closure(d, calendar_id):
            self.env['resource.calendar.leaves'].create({
                'name': 'Closure',
                'calendar_id': calendar_id,
                'company_id': company.id,
                'date_from': at(d, 6),
                'date_to': at(d, 18),
                'resource_id': False,
            })

        def approve_leave(leave_type, date_from, date_to):
            self.env['hr.leave'].create({
                'name': 'Leave',
                'employee_id': emp.id,
                'holiday_status_id': leave_type.id,
                'request_date_from': date_from,
                'request_date_to': date_to,
            }).action_approve()

        def row(d):
            return Report.search([
                ('employee_id', '=', emp.id), ('date', '=', d)])

        leave_type_excl = self.env['hr.leave.type'].create({
            'name': 'Leave excluding public holidays',
            'requires_allocation': False,
            'company_id': company.id,
            'include_public_holidays_in_duration': False,
        })
        leave_type_incl = self.env['hr.leave.type'].create({
            'name': 'Leave including public holidays',
            'requires_allocation': False,
            'company_id': company.id,
            'include_public_holidays_in_duration': True,
        })

        # contract: starts two weeks before week 0, ends week 5 Wednesday
        emp.contract_date_start = monday - timedelta(days=14)
        emp.contract_date_end = day(5, 2)

        # week 0 -- one attendance per day (Mon/Tue/Wed).  hr.attendance
        # worked_hours is calendar-aware (it discounts lunch breaks), so the
        # expected value is read back from the records, not hardcoded.
        attendances = self.env['hr.attendance'].create([
            {'employee_id': emp.id, 'check_in': at(day(0, 0), 12), 'check_out': at(day(0, 0), 17)},
            {'employee_id': emp.id, 'check_in': at(day(0, 1), 12), 'check_out': at(day(0, 1), 18)},
            {'employee_id': emp.id, 'check_in': at(day(0, 2), 12), 'check_out': at(day(0, 2), 20)},
        ])
        worked = {wd: round(att.worked_hours, 2)
                  for wd, att in zip((0, 1, 2), attendances)}
        closure(day(0, 4), calendar.id)               # public holiday, Friday

        # week 1 -- 3-day leave, type EXCLUDES holidays, holiday on Tuesday
        closure(day(1, 1), calendar.id)
        approve_leave(leave_type_excl, day(1, 0), day(1, 2))

        # week 2 -- 3-day leave, type INCLUDES holidays, holiday on Tuesday
        closure(day(2, 1), calendar.id)
        approve_leave(leave_type_incl, day(2, 0), day(2, 2))

        # week 3 -- company-wide closure (no calendar_id) on Monday
        closure(day(3, 0), False)

        # the report is an _auto=False SQL view, so searching it does not
        # flush the stored hr.attendance.worked_hours -- force it to the DB
        self.env.flush_all()

        # -- attendance: the report sums hr.attendance.worked_hours --------
        for wd in (0, 1, 2):
            self.assertRecordValues(row(day(0, wd)), [{
                'worked_hours': worked[wd],
                'expected_hours': 8.0,
                'leave_hours': 0.0,
                'difference_hours': round(worked[wd] - 8.0, 2),
            }])
        # plain working day: no attendance, no leave
        self.assertRecordValues(row(day(0, 3)), [{
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 0.0, 'difference_hours': -8.0}])

        # -- non-report days ---------------------------------------------
        self.assertFalse(row(day(0, 4)), "public holiday -> no row")
        self.assertFalse(row(day(0, 5)), "Saturday -> no row")
        self.assertFalse(row(day(0, 6)), "Sunday -> no row")
        self.assertFalse(row(day(3, 0)), "company-wide closure -> no row")

        # -- leave, type EXCLUDES public holidays (16h over 2 working days)
        self.assertRecordValues(row(day(1, 0)), [{
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 8.0, 'difference_hours': 0.0}])
        self.assertFalse(row(day(1, 1)), "public holiday inside leave -> no row")
        self.assertRecordValues(row(day(1, 2)), [{
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 8.0, 'difference_hours': 0.0}])

        # -- leave, type INCLUDES public holidays (24h over 3 working days)
        self.assertRecordValues(row(day(2, 0)), [{
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 8.0, 'difference_hours': 0.0}])
        self.assertFalse(row(day(2, 1)), "public holiday inside leave -> no row")
        self.assertRecordValues(row(day(2, 2)), [{
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 8.0, 'difference_hours': 0.0}])

        # -- contract bounds ---------------------------------------------
        self.assertFalse(row(monday - timedelta(days=21)),
                         "working day before contract start -> no row")
        self.assertRecordValues(row(day(5, 2)), [{   # last contracted day
            'worked_hours': 0.0, 'expected_hours': 8.0,
            'leave_hours': 0.0, 'difference_hours': -8.0}])
        self.assertFalse(row(day(5, 3)),
                         "working day after contract end -> no row")

    @freeze_time('2026-02-28')
    def test_overlap_leave_and_public_holiday_excluded(self):
        """ When the leave type excludes public holidays from its duration,
            the holiday is dropped from the leave's pro-rated working-day
            count (exercises the holiday anti-join in `leave_day`). """
        self.employee_emp.contract_date_start = "2026-02-01"
        self.env['resource.calendar.leaves'].create({
            'name': 'Some Public Holiday',
            'calendar_id': self.employee_emp.resource_calendar_id.id,
            'date_from': '2026-02-10 00:00:00',
            'date_to': '2026-02-10 18:00:00',
            'resource_id': False,
        })
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Count Public Holiday Leave',
            'requires_allocation': False,
            'company_id': self.company.id,
            'include_public_holidays_in_duration': False,
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
        # 2026-02-10 is a public holiday -> no report row; the leave's 16h are
        # spread over the 2 remaining working days -> 8h each.
        self.assertRecordValues(non_overlap_days, [{
            'expected_hours': 8.0,
            'leave_hours': 8.0,
            'difference_hours': 0.0,
        } for _ in range(2)])
