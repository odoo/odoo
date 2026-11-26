# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date

from odoo.tests import Form, tagged
from odoo.tests.common import HttpCase, TransactionCase, freeze_time


@tagged('post_install', '-at_install', 'attendance_overtime')
class TestOvertimeByDay(TransactionCase):
    """An attendance expects the hours of the schedule of the day it starts on, even over
    midnight."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # employee with a schedule (default company calendar, Mon-Fri 8-17)
        cls.employee_scheduled = cls.env['hr.employee'].create({
            'name': 'Scheduled Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
        })

        # employee with an undefined calendar -> expected = 0
        flex_calendar = cls.env['resource.calendar'].create({
            'name': 'Undefined Calendar',
            'calendar_type': 'undefined',
        })
        cls.employee_flex = cls.env['hr.employee'].create({
            'name': 'Flexible Employee',
            'tz': 'UTC',
            'resource_calendar_id': flex_calendar.id,
        })

    def test_flexible_cross_midnight(self):
        """Employee with no schedule works Jun 9 20:00 -> Jun 10 02:00 (6h) with a 3h break.
        Nothing is expected: the 3h worked are overtime."""
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 2, 0),
            'break_duration': 3.0,
        })
        self.assertRecordValues(attendance, [{'worked_hours': 3.0, 'expected_hours': 0.0, 'overtime_hours': 3.0}])

    def test_cross_midnight_expects_its_start_day(self):
        """Tuesday Jun 9 20:00 -> Wednesday 04:00 expects the 8h of Tuesday only: Wednesday's
        08:00-16:00 attendance still expects the 8h of Wednesday."""
        night, day = self.env['hr.attendance'].create([{
            'employee_id': self.employee_scheduled.id,
            'check_in': check_in,
            'check_out': check_out,
        } for check_in, check_out in (
            (datetime(2026, 6, 9, 20, 0), datetime(2026, 6, 10, 4, 0)),
            (datetime(2026, 6, 10, 8, 0), datetime(2026, 6, 10, 16, 0)),
        )])
        self.assertRecordValues(night | day, [
            {'worked_hours': 8.0, 'expected_hours': 8.0, 'overtime_hours': 0.0},
            {'worked_hours': 8.0, 'expected_hours': 8.0, 'overtime_hours': 0.0},
        ])

    def test_night_schedule_by_duration(self):
        """A night worker has a schedule by duration, 8h from Monday to Friday: each night expects the 8h of the
        day it starts on."""
        self.employee_scheduled.resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'Nights',
            'attendance_ids': [(0, 0, {'dayofweek': str(wd), 'duration_hours': 8}) for wd in range(5)],
        })
        night, long_night = self.env['hr.attendance'].create([{
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, day, 22, 0),  # Monday and Tuesday nights
            'check_out': datetime(2026, 6, day + 1, check_out_hour, 0),
        } for day, check_out_hour in ((8, 6), (9, 9))])
        self.assertRecordValues(night | long_night, [
            {'worked_hours': 8.0, 'expected_hours': 8.0, 'overtime_hours': 0.0},
            {'worked_hours': 11.0, 'expected_hours': 8.0, 'overtime_hours': 3.0},
        ])

    def test_partial_overtime_break_stays_on_source_else_branch(self):
        """
        Scheduled employee (Mon-Fri 8h/day) works 2026-06-09 (Tuesday) 08:00-19:00
        (11h gross) with a 1h break.  Net attended = 10h, scheduled = 8h, overtime = 2h.
        The attendance is left as recorded.
        """
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 19, 0),
            'break_duration': 1.0,
        })
        self.assertRecordValues(attendance, [{
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 19, 0),
            'break_duration': 1.0,
            'worked_hours': 10.0,
            'expected_hours': 8.0,
            'overtime_hours': 2.0,
        }])
        self.assertEqual(self.env['hr.attendance'].search_count([('employee_id', '=', self.employee_scheduled.id)]), 1)

    def test_long_cross_midnight_overtime(self):
        """Mon Jun 8 08:00 -> Tue Jun 9 02:00 (18h gross), break=2h: 16h worked for the 8h of
        Monday, 8h of overtime. Tuesday, worked from 08:00 to 16:00, expects its 8h on that
        attendance only."""
        night = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 8, 8, 0),
            'check_out': datetime(2026, 6, 9, 2, 0),
            'break_duration': 2.0,
        })
        day = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 16, 0),
        })
        self.assertRecordValues(night | day, [
            {'worked_hours': 16.0, 'expected_hours': 8.0, 'overtime_hours': 8.0},
            {'worked_hours': 8.0, 'expected_hours': 8.0, 'overtime_hours': 0.0},
        ])


@tagged('post_install', '-at_install', 'attendance_overtime')
class TestAttendanceOvertime(TransactionCase):
    """The overtime of an attendance: its worked hours minus its share of the expected hours of
    its days."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # default company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Overtime Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
        })

    def _create(self, check_in, check_out, **vals):
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
            **vals,
        })

    def test_overtime(self):
        # Monday, 13h for 8h scheduled
        attendance = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        self.assertRecordValues(attendance, [{'expected_hours': 8.0, 'overtime_hours': 5.0}])

    def test_no_overtime_within_schedule(self):
        attendance = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))
        self.assertRecordValues(attendance, [{'expected_hours': 8.0, 'overtime_hours': 0.0}])

    def test_entirely_overtime_on_day_off(self):
        # Saturday: nothing scheduled, the whole attendance is overtime
        attendance = self._create(datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))
        self.assertRecordValues(attendance, [{'expected_hours': 0.0, 'overtime_hours': 3.0}])

    def test_counts_other_attendances_of_the_day(self):
        morning = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 12, 0))
        # 4h + 7h = 11h: the last 3h are overtime
        afternoon = self._create(datetime(2026, 6, 8, 13, 0), datetime(2026, 6, 8, 20, 0))
        self.assertRecordValues(morning | afternoon, [
            {'expected_hours': 4.0, 'overtime_hours': 0.0},
            {'expected_hours': 4.0, 'overtime_hours': 3.0},
        ])

    def test_overtime_cases(self):
        cases = [
            (datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0), 0.0, 5.0),
            (datetime(2026, 6, 9, 7, 0), datetime(2026, 6, 9, 20, 0), 1.0, 4.0),
            # crosses midnight: 12.5h worked for the 8h of its start day
            (datetime(2026, 6, 10, 20, 0), datetime(2026, 6, 11, 9, 0), 0.5, 4.5),
            (datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0), 0.0, 3.0),  # day off
        ]
        for check_in, check_out, break_duration, overtime in cases:
            with self.subTest(check_in=check_in, break_duration=break_duration):
                attendance = self._create(check_in, check_out, break_duration=break_duration)
                self.assertAlmostEqual(attendance.overtime_hours, overtime, places=4)

    def test_form_attendance_reviewed_at_once(self):
        with Form(self.env['hr.attendance']) as form:
            form.employee_id = self.employee
            form.check_in = datetime(2026, 6, 8, 7, 0)
            form.check_out = datetime(2026, 6, 8, 20, 0)
        self.assertRecordValues(form.record, [{'state': 'validated', 'overtime_hours': 5.0}])
        self.assertEqual(self.employee.total_overtime, 5.0)

        # an attendance of a manager is reviewed at once, one from the kiosk waits for a review
        self.env.company.attendance_validation = 'manual_validation'
        draft = self._create(datetime(2026, 6, 9, 7, 0), datetime(2026, 6, 9, 20, 0), in_mode='kiosk', out_mode='kiosk')
        self.assertRecordValues(draft, [{'state': 'draft', 'overtime_hours': 5.0}])
        self.assertEqual(self.employee.total_overtime, 5.0, "the overtime of a draft attendance waits for its review")


@tagged('post_install', '-at_install', 'attendance_overtime')
class TestCheckOutOvertime(HttpCase):
    """The overtime of the day given by the systray and kiosk check-out routes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Check-Out Overtime Company'})
        cls.user = cls.env['res.users'].create({
            'name': 'overtime_user',
            'login': 'overtime_user',
            'password': 'overtime_user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        # company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Overtime Employee',
            'company_id': cls.company.id,
            'user_id': cls.user.id,
            'tz': 'UTC',
            'barcode': 'OVERTIME123',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
        })

    def _check_in(self, check_in):
        # a check-in from a device: a manual one waits for a manager at check-out
        self.env['hr.attendance'].with_company(self.company).create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'in_mode': 'systray',
        })

    def _systray_check_out(self):
        self.authenticate('overtime_user', 'overtime_user')
        return self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})

    @freeze_time('2026-06-08 17:00:00')  # Monday
    def test_systray_check_out_overtime(self):
        # within the tolerance, the day has no overtime: it is reviewed at check-out
        self.company.attendance_validation_tolerance = 60
        self._check_in(datetime(2026, 6, 8, 8, 0))
        result = self._systray_check_out()
        self.assertEqual(self.employee.attendance_state, 'checked_out')
        self.assertEqual(self.employee.last_attendance_id.state, 'validated')
        self.assertFalse(result['overtime_today'])
        self.assertFalse(result['total_overtime'])

    @freeze_time('2026-06-08 20:00:00')
    def test_systray_check_out_overtime_pending_validation(self):
        self.company.attendance_validation = 'manual_validation'
        self._check_in(datetime(2026, 6, 8, 7, 0))
        result = self._systray_check_out()
        self.assertEqual(self.employee.last_attendance_id.state, 'draft')
        self.assertAlmostEqual(result['overtime_today'], 5.0)
        self.assertAlmostEqual(result['total_overtime'], 0.0, msg="the overtime waits for the review")

    @freeze_time('2026-06-08 16:00:00')
    def test_systray_check_out_without_overtime(self):
        self._check_in(datetime(2026, 6, 8, 8, 0))
        result = self._systray_check_out()
        self.assertFalse(result['overtime_today'])

    @freeze_time('2026-06-08 08:00:00')
    def test_systray_check_in_has_no_overtime(self):
        result = self._systray_check_out()
        self.assertEqual(self.employee.attendance_state, 'checked_in')
        self.assertFalse(result['overtime_today'])

    @freeze_time('2026-06-08 17:00:00')
    def test_kiosk_check_out_overtime(self):
        self._check_in(datetime(2026, 6, 8, 8, 0))
        result = self.make_jsonrpc_request('/hr_attendance/attendance_barcode_scanned', {
            'token': self.company.attendance_kiosk_key,
            'barcode': 'OVERTIME123',
        })
        self.assertEqual(self.employee.attendance_state, 'checked_out')
        self.assertAlmostEqual(result['overtime_today'], 1.0)
