# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests.common import TransactionCase, freeze_time, tagged


@tagged('post_install', '-at_install', 'hr_attendance_automatic_break')
class TestHrAttendanceAutomaticBreak(TransactionCase):
    """Automatic break of the time rules, applied at check-out.

    Two employees share the same time type but not the same schedule: 8h a day and 10h a
    day. Two tiered rules give them a different break: 0:30 between 6h and 9h of scheduled
    work, 0:45 between 9h and 24h.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.tz = 'UTC'
        cls.att_type = cls.company._get_default_attendance_work_entry_type()
        cls.company.attendance_work_entry_type_id = cls.att_type

        def calendar(name, morning, afternoon):
            return cls.env['resource.calendar'].create({
                'name': name,
                'attendance_ids': [
                    (0, 0, {'dayofweek': wd, 'hour_from': hour_from, 'hour_to': hour_to})
                    for wd in ['0', '1', '2', '3', '4']
                    for hour_from, hour_to in (morning, afternoon)
                ],
            })

        cls.employee_8h = cls.env['hr.employee'].create({
            'name': 'Employee 8h',
            'tz': 'UTC',
            'resource_calendar_id': calendar('8h/day', (8, 12), (13, 17)).id,
        })
        cls.employee_10h = cls.env['hr.employee'].create({
            'name': 'Employee 10h',
            'tz': 'UTC',
            'resource_calendar_id': calendar('10h/day', (7, 12), (13, 18)).id,
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.env['hr.time.rule'].create([{
            'name': 'Break 6h-9h',
            'company_id': cls.company.id,
            'condition_work_entry_type_ids': [(6, 0, cls.att_type.ids)],
            'automatic_break': True,
            'break_min_work_hours': 6.0,
            'break_max_work_hours': 9.0,
            'automatic_break_duration': 0.5,
        }, {
            'name': 'Break 9h-24h',
            'company_id': cls.company.id,
            'condition_work_entry_type_ids': [(6, 0, cls.att_type.ids)],
            'automatic_break': True,
            'break_min_work_hours': 9.0,
            'break_max_work_hours': 24.0,
            'automatic_break_duration': 0.75,
        }])

    def assertAttendance(self, attendance, check_out, break_duration, worked_hours):
        self.assertEqual(attendance.check_out, check_out)
        self.assertAlmostEqual(attendance.break_duration, break_duration, places=4)
        self.assertAlmostEqual(attendance.worked_hours, worked_hours, places=4)

    def test_check_in_out_action(self):
        """Checking out from the systray or the kiosk records the automatic break."""
        employees = self.employee_8h | self.employee_10h
        with freeze_time('2026-11-09 08:00:00'):  # Monday
            for employee in employees:
                employee._attendance_action_change()
        with freeze_time('2026-11-09 12:00:00'):
            for employee in employees:
                employee._attendance_action_change()

        check_out = datetime(2026, 11, 9, 12, 0)
        self.assertAttendance(self.employee_8h.last_attendance_id, check_out, 0.5, 3.5)
        self.assertAttendance(self.employee_10h.last_attendance_id, check_out, 0.75, 3.25)

    def test_create_closed_attendance(self):
        """Creating a closed attendance (e.g. from the form, which sends a 0 break) records
        the automatic break."""
        att_8h, att_10h = self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
            'check_out': datetime(2026, 11, 9, 16, 0),
            'break_duration': 0.0,
        } for employee in (self.employee_8h, self.employee_10h)])

        check_out = datetime(2026, 11, 9, 16, 0)
        self.assertAttendance(att_8h, check_out, 0.5, 7.5)
        self.assertAttendance(att_10h, check_out, 0.75, 7.25)

    def test_close_open_attendance(self):
        """Setting the check-out of an open attendance records the automatic break."""
        att_8h, att_10h = self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        } for employee in (self.employee_8h, self.employee_10h)])
        self.assertFalse(att_8h.break_duration)
        self.assertFalse(att_10h.break_duration)

        check_out = datetime(2026, 11, 9, 12, 0)
        (att_8h | att_10h).write({'check_out': check_out})

        self.assertAttendance(att_8h, check_out, 0.5, 3.5)
        self.assertAttendance(att_10h, check_out, 0.75, 3.25)

    @freeze_time('2026-11-09 23:00:00')
    def test_auto_check_out_tolerance(self):
        """In tolerance mode, the automatic check-out is check-in + schedule + break +
        tolerance, and the break is recorded."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'tolerance',
            'auto_check_out_tolerance': 1.0,
        })
        att_8h, att_10h = self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        } for employee in (self.employee_8h, self.employee_10h)])

        self.env['hr.attendance']._cron_auto_check_out()

        # 08:00 + 8h + 0:30 + 1h
        self.assertAttendance(att_8h, datetime(2026, 11, 9, 17, 30), 0.5, 9.0)
        # 08:00 + 10h + 0:45 + 1h
        self.assertAttendance(att_10h, datetime(2026, 11, 9, 19, 45), 0.75, 11.0)
        self.assertEqual((att_8h | att_10h).mapped('out_mode'), ['auto_check_out'] * 2)

    @freeze_time('2026-11-09 19:00:00')
    def test_auto_check_out_specific_time(self):
        """In specific time mode, the automatic check-out stays at the cutoff and the break
        is recorded."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 18.0,
        })
        att_8h, att_10h = self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        } for employee in (self.employee_8h, self.employee_10h)])

        self.env['hr.attendance']._cron_auto_check_out()

        check_out = datetime(2026, 11, 9, 18, 0)
        self.assertAttendance(att_8h, check_out, 0.5, 9.5)
        self.assertAttendance(att_10h, check_out, 0.75, 9.25)
        self.assertEqual((att_8h | att_10h).mapped('out_mode'), ['auto_check_out'] * 2)
