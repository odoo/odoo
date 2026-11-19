# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests.common import TransactionCase, freeze_time, tagged


@tagged('post_install', '-at_install', 'hr_attendance_automatic_break')
class TestHrAttendanceAutomaticBreak(TransactionCase):
    """Automatic break of the time rules: recorded once per day when the rule applies, the breaks
    of the rules applying adding up.

    The employee works 8h a day (08:00-12:00, 13:00-17:00) and a daily overtime rule on the
    attendance time type gives a 15 minutes break.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.tz = 'UTC'
        cls.att_type = cls.company._get_default_attendance_work_entry_type()
        cls.company.attendance_work_entry_type_id = cls.att_type

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
            'resource_calendar_id': cls.env['resource.calendar'].create({
                'name': '8h/day',
                'attendance_ids': [
                    (0, 0, {'dayofweek': wd, 'hour_from': hour_from, 'hour_to': hour_to})
                    for wd in ['0', '1', '2', '3', '4']
                    for hour_from, hour_to in ((8, 12), (13, 17))
                ],
            }).id,
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Automatic Break Overtime',
            'code': 'OT_AUTO_BREAK_TEST',
        })
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Overtime with automatic break',
            'company_id': cls.company.id,
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [(6, 0, cls.att_type.ids)],
            'automatic_break_duration': 15,
        })

    def _get_day_attendances(self, day):
        return self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', datetime(2026, 11, day)),
            ('check_in', '<', datetime(2026, 11, day + 1)),
        ], order='check_in')

    def assertDay(self, day, break_duration, worked_hours, overtime=None):
        """Check the totals of the attendances of a day of November 2026: the time rules may
        have split the attendances, spreading their break over the parts."""
        attendances = self._get_day_attendances(day)
        self.assertAlmostEqual(sum(attendances.mapped('break_duration')), break_duration, places=4)
        self.assertAlmostEqual(sum(attendances.mapped('worked_hours')), worked_hours, places=4)
        if overtime is not None:
            outputs = attendances.filtered(lambda a: a.work_entry_type_id == self.ot_type)
            self.assertAlmostEqual(sum(outputs.mapped('worked_hours')), overtime, places=4)

    def test_no_break_within_schedule(self):
        """No automatic break while the worked time does not exceed the expected hours."""
        with freeze_time('2026-11-09 08:00:00'):  # Monday
            self.employee._attendance_action_change()
        with freeze_time('2026-11-09 12:00:00'):
            self.employee._attendance_action_change()
        self.assertDay(9, 0.0, 4.0)

        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 10, 8, 0),
            'check_out': datetime(2026, 11, 10, 16, 0),
        })
        self.assertDay(10, 0.0, 8.0, overtime=0.0)

    def test_check_in_out_action(self):
        """Checking out from the systray or the kiosk after the schedule records the break."""
        with freeze_time('2026-11-09 08:00:00'):
            self.employee._attendance_action_change()
        with freeze_time('2026-11-09 18:00:00'):
            self.employee._attendance_action_change()

        self.assertDay(9, 0.25, 9.75, overtime=1.75)

    def test_create_closed_attendance(self):
        """Creating a closed attendance (e.g. from the form, which sends a 0 break) exceeding the
        schedule records the break."""
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
            'check_out': datetime(2026, 11, 9, 17, 30),
            'break_duration': 0.0,
        })

        self.assertDay(9, 0.25, 9.25, overtime=1.25)

    def test_close_open_attendance(self):
        """Setting the check-out of an open attendance after the schedule records the break."""
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        })

        attendance.write({'check_out': datetime(2026, 11, 9, 18, 0)})

        self.assertDay(9, 0.25, 9.75, overtime=1.75)

    def test_full_break_on_small_excess(self):
        """The whole break is given, even when the excess is shorter than the break."""
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
            'check_out': datetime(2026, 11, 9, 16, 10),
        })

        # 8:10 worked: 7:55 left after the break
        self.assertDay(9, 0.25, 8 + 10 / 60 - 0.25, overtime=0.0)

    def test_break_within_employer_tolerance(self):
        """The rule, hence its break, only applies above its tolerance."""
        self.rule.employer_tolerance = 1.0
        self.env['hr.attendance'].create([{
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
            'check_out': datetime(2026, 11, 9, 16, 30),
        }, {
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 10, 8, 0),
            'check_out': datetime(2026, 11, 10, 17, 30),
        }])

        self.assertDay(9, 0.0, 8.5, overtime=0.0)
        # 9:30 worked: break given, 9:15 left, still 1:15 of overtime above the tolerance
        self.assertDay(10, 0.25, 9.25, overtime=1.25)

    def _create_break_rules(self, rules):
        """Replace the rule by break rules on fixed daily hours.

        :param list rules: ``(sequence, expected hours, break minutes)``
        """
        self.rule.active = False
        return self.env['hr.time.rule'].create([{
            'name': f'Break of {minutes} minutes above {hours}h',
            'company_id': self.company.id,
            'sequence': sequence,
            'working_hours_mode': 'day',
            'expected_hours': hours,
            'condition_work_entry_type_ids': [(6, 0, self.att_type.ids)],
            'automatic_break_duration': minutes,
        } for sequence, hours, minutes in rules])

    def _create_attendance(self, day, hours, minutes):
        """Create an attendance from 08:00 on a day of November 2026."""
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, day, 8, 0),
            'check_out': datetime(2026, 11, day, 8 + hours, minutes),
        })

    def test_tiered_breaks(self):
        """The breaks of the rules applying add up; each rule is checked, in sequence, on the
        worked time minus the breaks of the previous rules applied."""
        self._create_break_rules([(1, 3.0, 15), (2, 8.0, 30)])
        for day, (hours, minutes) in zip((9, 10, 11, 12), ((3, 0), (4, 0), (8, 5), (8, 20))):
            self._create_attendance(day, hours, minutes)

        self.assertDay(9, 0.0, 3.0)  # no rule exceeded
        self.assertDay(10, 0.25, 3.75)  # above 3h
        self.assertDay(11, 0.25, 8 + 5 / 60 - 0.25)  # 7:50 left, not above 8h
        self.assertDay(12, 0.75, 8 + 20 / 60 - 0.75)  # 8:05 left, above 8h: 7:35 left

    def test_breaks_in_sequence(self):
        """A rule not applying is skipped, the next ones are still checked; the sequence of the
        rules decides which breaks are given."""
        rules = self._create_break_rules([(1, 3.0, 5), (2, 7.0, 15), (3, 4.0, 10), (4, 5.0, 15)])
        self._create_attendance(9, 5, 10)
        # 5:10 > 3h: 5 minutes, 5:05 < 7h: skipped, 5:05 > 4h: 10 minutes, 4:55 < 5h: skipped
        self.assertDay(9, 0.25, 5 + 10 / 60 - 0.25)

        # the 5h rule checked before the 4h one: 5:05 > 5h: 15 minutes, 4:50 > 4h: 10 minutes
        rules[3].sequence = 3
        rules[2].sequence = 4
        self._create_attendance(10, 5, 10)
        self.assertDay(10, 0.5, 5 + 10 / 60 - 0.5)

    def test_one_break_per_day(self):
        """The break is recorded once per day, on the attendance exceeding the schedule."""
        for check_in, check_out in (('08:00', '12:00'), ('13:00', '17:00'), ('17:30', '19:00')):
            with freeze_time(f'2026-11-09 {check_in}:00'):
                self.employee._attendance_action_change()
            with freeze_time(f'2026-11-09 {check_out}:00'):
                self.employee._attendance_action_change()

        attendances = self._get_day_attendances(9)
        self.assertEqual(attendances[:2].mapped('break_duration'), [0.0, 0.0])
        self.assertDay(9, 0.25, 9.25, overtime=1.25)

    def test_manual_break_kept(self):
        """A break given by the employee or a manager is not overwritten nor topped up."""
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
            'check_out': datetime(2026, 11, 9, 18, 0),
            'break_duration': 0.5,
        })

        self.assertDay(9, 0.5, 9.5, overtime=1.5)

    @freeze_time('2026-11-09 23:00:00')
    def test_auto_check_out_tolerance(self):
        """In tolerance mode, the automatic check-out is check-in + schedule + break + tolerance,
        and the break is recorded."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'tolerance',
            'auto_check_out_tolerance': 1.0,
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        })

        self.env['hr.attendance']._cron_auto_check_out()

        # 08:00 + 8h + 0:15 + 1h
        self.assertEqual(max(self._get_day_attendances(9).mapped('check_out')), datetime(2026, 11, 9, 17, 15))
        self.assertEqual(attendance.out_mode, 'auto_check_out')
        self.assertDay(9, 0.25, 9.0, overtime=1.0)

    @freeze_time('2026-11-09 19:00:00')
    def test_auto_check_out_specific_time(self):
        """In specific time mode, the automatic check-out stays at the cutoff and the break is
        recorded."""
        self.company.write({
            'auto_check_out': True,
            'auto_check_out_mode': 'specific_time',
            'auto_check_out_specific_time': 18.0,
        })
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 11, 9, 8, 0),
        })

        self.env['hr.attendance']._cron_auto_check_out()

        self.assertEqual(max(self._get_day_attendances(9).mapped('check_out')), datetime(2026, 11, 9, 18, 0))
        self.assertEqual(attendance.out_mode, 'auto_check_out')
        self.assertDay(9, 0.25, 9.75, overtime=1.75)
