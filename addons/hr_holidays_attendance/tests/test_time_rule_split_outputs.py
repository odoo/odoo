# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase, freeze_time


class TimeRuleOutputsCommon:
    """Helpers reading the time off written by the time rules for the attendances."""

    def _hours(self, leaves):
        return sum((leave.date_to - leave.date_from).total_seconds() / 3600 for leave in leaves)

    def _outputs(self, employee):
        """The time off written by the time rules for the employee, in chronological order."""
        return self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('time_rule_id', '!=', False),
        ], order='date_from')

    def _attendances(self, employee):
        return self.env['hr.attendance'].search([('employee_id', '=', employee.id)], order='check_in')

    def _assert_attendance_kept(self, attendance, check_in, check_out, break_duration=0.0):
        """The attendance stays as recorded: no cut, no type, its break is kept."""
        self.assertEqual(attendance.check_in, check_in)
        self.assertEqual(attendance.check_out, check_out)
        self.assertAlmostEqual(attendance.break_duration, break_duration, places=4)
        self.assertEqual(self._attendances(attendance.employee_id), attendance, "no other attendance is created")


@tagged('post_install', '-at_install', 'time_rule_pipeline')
class TestTimeRuleSplitOutputs(TimeRuleOutputsCommon, TransactionCase):
    """Time off written for attendances: break and day boundaries."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')
        calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = calendar
        cls.att_type = cls.env.ref('hr_work_entry.generic_work_entry_type_attendance')
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Pipeline Test Overtime',
            'code': 'OT_PIPELINE_TEST',
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Pipeline Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [Command.link(cls.att_type.id)],
        })

        # employee with a schedule (company calendar, Mon-Fri 8h a day)
        cls.employee_scheduled = cls.env['hr.employee'].create({
            'name': 'Scheduled Employee',
            'tz': 'UTC',
            'work_entry_source': 'attendance',
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
            'work_entry_source': 'attendance',
            'resource_calendar_id': flex_calendar.id,
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
        })

    # A flexible employee has no expected hours: the time off of its attendance (check in to check
    # out minus the break, so the break is taken at the end) is what the rules evaluate. The
    # rules based on the employee schedule skip the fully flexible days, so these tests use a
    # rule without schedule and without threshold (every hour is an excess, each calendar day
    # being evaluated apart), restricted to the flexible employee.

    def _create_flex_rule(self):
        return self.env['hr.time.rule'].create({
            'name': 'Flexible Overtime (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 0.0,
            'employee_domain': str([('id', '=', self.employee_flex.id)]),
            'work_entry_type_id': self.ot_type.id,
            'condition_work_entry_type_ids': [Command.link(self.att_type.id)],
        })

    def test_cross_midnight_break_outputs_flex(self):
        """Jun 9 20:00 -> Jun 10 02:00 (6h) with a 3h break: the worked time off is 20:00 -> 23:00,
        so one output of 3h (worked hours minus the break), nothing is left after midnight."""
        flex_rule = self._create_flex_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 2, 0),
            'break_duration': 3.0,
        })
        outputs = self._outputs(self.employee_flex)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs.work_entry_type_id, self.ot_type)
        self.assertEqual(outputs.time_rule_id, flex_rule)
        self.assertEqual(outputs.date_from, datetime(2026, 6, 9, 20, 0))
        self.assertEqual(outputs.date_to, datetime(2026, 6, 9, 23, 0))
        self.assertAlmostEqual(self._hours(outputs), att.worked_hours, places=4)
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 20, 0), datetime(2026, 6, 10, 2, 0), 3.0)

    def test_seconds_kept_flex(self):
        """Jun 9 08:00:00 -> 17:00:05: the time off of the attendance, so its output, keep the seconds."""
        self._create_flex_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 17, 0, 5),
        })
        output = self._outputs(self.employee_flex)
        self.assertEqual((output.date_from, output.date_to), (att.check_in, att.check_out))

    def test_zero_break_outputs_one_per_day_flex(self):
        """Same without break: the 6h time off is cut at midnight, 4h on Jun 9 and 2h on Jun 10."""
        self._create_flex_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 2, 0),
            'break_duration': 0.0,
        })
        day1, day2 = self._outputs(self.employee_flex)
        self.assertEqual(day1.work_entry_type_id | day2.work_entry_type_id, self.ot_type)
        self.assertEqual(day1.date_from, datetime(2026, 6, 9, 20, 0))
        self.assertAlmostEqual(self._hours(day1), 4.0, delta=1e-3)
        self.assertEqual(day2.date_from, datetime(2026, 6, 10, 0, 0))
        self.assertEqual(day2.date_to, datetime(2026, 6, 10, 2, 0))
        self.assertAlmostEqual(self._hours(day1) + self._hours(day2), att.worked_hours, places=3)
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 20, 0), datetime(2026, 6, 10, 2, 0))

    def test_three_day_span_outputs_net_of_break_flex(self):
        """Jun 8 22:00 -> Jun 10 03:00 (29h) with a 2.9h break: the worked time off ends 2.9h before
        the check out, Jun 10 00:06. One output per calendar day: 2h, 24h, then 0.1h.
        Together they are the worked hours of the attendance (29h - 2.9h)."""
        self._create_flex_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 8, 22, 0),
            'check_out': datetime(2026, 6, 10, 3, 0),
            'break_duration': 2.9,
        })
        day1, day2, day3 = self._outputs(self.employee_flex)
        self.assertEqual(day1.date_from, datetime(2026, 6, 8, 22, 0))
        self.assertAlmostEqual(self._hours(day1), 2.0, delta=1e-3)
        self.assertEqual(day2.date_from, datetime(2026, 6, 9, 0, 0))
        self.assertAlmostEqual(self._hours(day2), 24.0, delta=1e-3)
        self.assertEqual(day3.date_from, datetime(2026, 6, 10, 0, 0))
        self.assertEqual(day3.date_to, datetime(2026, 6, 10, 0, 6))
        self.assertAlmostEqual(self._hours(day1 | day2 | day3), 29 - 2.9, delta=1e-3)
        self.assertAlmostEqual(att.worked_hours, 29 - 2.9, places=4)
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 22, 0), datetime(2026, 6, 10, 3, 0), 2.9)

    def test_multiday_break_at_the_end_outputs(self):
        """Scheduled employee Mon Jun 8 08:00 -> Tue Jun 9 02:00 (18h gross), break 2h: the rules see
        08:00 -> midnight, the break being at the end.

        Monday: 16h worked, 8h expected: the excess is the last 8h, 16:00 -> midnight.
        Tuesday: nothing worked once the break is taken: no output.
        """
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 8, 8, 0),
            'check_out': datetime(2026, 6, 9, 2, 0),
            'break_duration': 2.0,
        })
        outputs = self._outputs(self.employee_scheduled)
        self.assertEqual(len(outputs), 1, "one output for the Monday excess, none for Tuesday")
        self.assertEqual(outputs.attendance_id, att)
        self.assertEqual(outputs.work_entry_type_id, self.ot_type)
        self.assertEqual(outputs.date_from.replace(microsecond=0), datetime(2026, 6, 8, 16, 0))
        self.assertAlmostEqual(self._hours(outputs), 8.0, delta=1e-3)
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 9, 2, 0), 2.0)

    def test_single_day_two_rules_break_kept_on_attendance(self):
        """Scheduled employee Jun 9 08:00-22:00 (14h gross), break 1h at the end: 08:00-21:00 worked,
        8h scheduled.

        Rule 1: 5h excess -> OT1 [16:00-21:00].
        Rule 2 (3h of OT1 a day -> OT2): 2h over the 3h -> OT2 is the last 2h of the slice.
        The two outputs are adjacent and cover [16:00-21:00]; the break stays on the attendance.
        """
        ot2_type = self.env['hr.work.entry.type'].create({
            'name': 'High Overtime (Pipeline Test)',
            'code': 'OT2_PIPELINE_TEST',
        })
        self.env['hr.time.rule'].create({
            'name': 'High Overtime Rule (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 3.0,
            'work_entry_type_id': ot2_type.id,
            'condition_work_entry_type_ids': [Command.link(self.ot_type.id)],
            'sequence': 20,
        })
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 22, 0),
            'break_duration': 1.0,
        })
        ot1, ot2 = self._outputs(self.employee_scheduled)
        self.assertEqual((ot1.work_entry_type_id, ot2.work_entry_type_id), (self.ot_type, ot2_type))
        self.assertEqual(ot1.attendance_id | ot2.attendance_id, att)
        self.assertEqual(ot1.date_from, datetime(2026, 6, 9, 16, 0))
        self.assertEqual(ot1.date_to, ot2.date_from, "the outputs are adjacent")
        self.assertEqual(ot2.date_to, datetime(2026, 6, 9, 21, 0))
        self.assertAlmostEqual(self._hours(ot2), 2.0, delta=1e-3)
        self.assertAlmostEqual(self._hours(ot1 | ot2), 5.0, delta=1e-3)
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 8, 0), datetime(2026, 6, 9, 22, 0), 1.0)

    def test_multiday_two_rules_outputs_flex(self):
        """Flex Jun 9 20:00 -> Jun 10 04:00 (8h), break 2h: the worked time off is 20:00 -> 02:00 (6h).

        Rule 1: all of it is OT1, one slice per day: 20:00-24:00 and 00:00-02:00.
        Rule 2 (2h of OT1 a day -> OT2): Jun 9 slice is 4h, 2h over: OT2 [22:00-24:00],
        OT1 [20:00-22:00]. The Jun 10 slice is 2h, not over: it stays OT1.
        """
        self._create_flex_rule()
        ot2_type = self.env['hr.work.entry.type'].create({
            'name': 'High Overtime (Pipeline Test)',
            'code': 'OT2_PIPELINE_TEST',
        })
        self.env['hr.time.rule'].create({
            'name': 'High Overtime Rule (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 2.0,
            'work_entry_type_id': ot2_type.id,
            'condition_work_entry_type_ids': [Command.link(self.ot_type.id)],
            'sequence': 20,
        })
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 4, 0),
            'break_duration': 2.0,
        })
        ot1_d1, ot2_d1, ot1_d2 = self._outputs(self.employee_flex)
        self.assertEqual((ot1_d1.work_entry_type_id, ot2_d1.work_entry_type_id, ot1_d2.work_entry_type_id),
                         (self.ot_type, ot2_type, self.ot_type))
        self.assertEqual((ot1_d1.date_from, ot1_d1.date_to), (datetime(2026, 6, 9, 20, 0), datetime(2026, 6, 9, 22, 0)))
        self.assertEqual(ot2_d1.date_from, datetime(2026, 6, 9, 22, 0))
        self.assertAlmostEqual(self._hours(ot2_d1), 2.0, delta=1e-3)
        self.assertEqual((ot1_d2.date_from, ot1_d2.date_to), (datetime(2026, 6, 10, 0, 0), datetime(2026, 6, 10, 2, 0)))
        self.assertAlmostEqual(self._hours(ot1_d1 | ot2_d1 | ot1_d2), 6.0, delta=1e-3)
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 20, 0), datetime(2026, 6, 10, 4, 0), 2.0)

    def _create_night_rule(self):
        night_type = self.env['hr.work.entry.type'].create({
            'name': 'Night Work (Pipeline Test)',
            'code': 'NIGHT_PIPELINE_TEST',
        })
        self.rule.active = False
        return self.env['hr.time.rule'].create({
            'name': 'Night Work Rule (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 0.0,
            'timing_start': 0.0,
            'timing_stop': 5.0,
            'work_entry_type_id': night_type.id,
            'condition_work_entry_type_ids': [Command.link(self.att_type.id)],
        })

    def test_output_at_check_in_break_kept_on_attendance(self):
        """A rule whose output starts at check-in (night work before 05:00).

        Scheduled employee Jun 9 03:00-12:00 (9h gross), break 1h. The night rule has no threshold,
        so the window 03:00-05:00 is one output of 2h; the attendance is not cut and keeps its break.
        """
        night_rule = self._create_night_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 3, 0),
            'check_out': datetime(2026, 6, 9, 12, 0),
            'break_duration': 1.0,
        })
        night = self._outputs(self.employee_scheduled)
        self.assertEqual(len(night), 1)
        self.assertEqual(night.time_rule_id, night_rule)
        self.assertEqual(night.work_entry_type_id, night_rule.work_entry_type_id)
        self.assertEqual(night.attendance_id, att)
        self.assertEqual((night.date_from, night.date_to), (datetime(2026, 6, 9, 3, 0), datetime(2026, 6, 9, 5, 0)))
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 3, 0), datetime(2026, 6, 9, 12, 0), 1.0)

    def test_output_at_check_in_break_longer_than_output(self):
        """Same with a break longer than the night window (2.5h > 2h): no error, same output."""
        self._create_night_rule()
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 3, 0),
            'check_out': datetime(2026, 6, 9, 12, 0),
            'break_duration': 2.5,
        })
        night = self._outputs(self.employee_scheduled)
        self.assertEqual(len(night), 1)
        self.assertEqual((night.date_from, night.date_to), (datetime(2026, 6, 9, 3, 0), datetime(2026, 6, 9, 5, 0)))
        self._assert_attendance_kept(att, datetime(2026, 6, 9, 3, 0), datetime(2026, 6, 9, 12, 0), 2.5)

    def test_cross_midnight_break_dst_timezone_flex(self):
        """Europe/Brussels, Mar 28 2026 20:00 -> Mar 29 04:00 local (clocks go forward at 02:00),
        i.e. 19:00 -> 02:00 UTC = 7h, break 3.5h: the worked time off ends 3.5h before the check out,
        22:30 UTC (23:30 local), still on Mar 28. One output of 3.5h, 19:00 -> 22:30 UTC."""
        self._create_flex_rule()
        self.employee_flex.tz = 'Europe/Brussels'
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 3, 28, 19, 0),
            'check_out': datetime(2026, 3, 29, 2, 0),
            'break_duration': 3.5,
        })
        outputs = self._outputs(self.employee_flex)
        self.assertEqual(len(outputs), 1)
        self.assertEqual((outputs.date_from, outputs.date_to), (datetime(2026, 3, 28, 19, 0), datetime(2026, 3, 28, 22, 30)))
        self.assertAlmostEqual(self._hours(outputs), att.worked_hours, places=4)
        self._assert_attendance_kept(att, datetime(2026, 3, 28, 19, 0), datetime(2026, 3, 29, 2, 0), 3.5)


@tagged('post_install', '-at_install', 'time_rule_pipeline')
class TestAttendanceOutputs(TimeRuleOutputsCommon, TransactionCase):
    """Output time off of an attendance: what the old split preview and chatter showed."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.att_type = cls.env.ref('hr_work_entry.generic_work_entry_type_attendance')
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Preview Test Overtime',
            'code': 'OT_PREVIEW_TEST',
        })
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Preview Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [Command.link(cls.att_type.id)],
        })
        # default company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Preview Employee',
            'tz': 'UTC',
            'work_entry_source': 'attendance',
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

    def test_overtime_output_of_long_day(self):
        # Monday, 13h for 8h scheduled: the excess is the last 5h
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual(output.work_entry_type_id, self.ot_type)
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 8, 15, 0), datetime(2026, 6, 8, 20, 0)))
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))

    def test_no_output_within_schedule(self):
        att = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))
        self.assertFalse(self._outputs(self.employee))
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))

    def test_output_entirely_overtime_on_day_off(self):
        # Saturday: nothing scheduled, the whole attendance is excess
        self._create(datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual(output.work_entry_type_id, self.ot_type)
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0)))

    def test_output_counts_other_attendances_of_the_day(self):
        first = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 12, 0))
        self.assertFalse(self._outputs(self.employee))
        # 4h + 7h = 11h: the last 3h are overtime, linked to the attendance that goes over
        second = self._create(datetime(2026, 6, 8, 13, 0), datetime(2026, 6, 8, 20, 0))
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual(output.attendance_id, second)
        self.assertFalse(first.related_leave_ids)
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 8, 17, 0), datetime(2026, 6, 8, 20, 0)))
        self.assertEqual(self._attendances(self.employee), first | second)
        self.assertEqual((second.check_in, second.check_out), (datetime(2026, 6, 8, 13, 0), datetime(2026, 6, 8, 20, 0)))

    def test_outputs_of_various_days(self):
        # (check in, check out, break, expected outputs as (start, hours); the day end is 23:59:59)
        cases = [
            (datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0), 0.0,
             [(datetime(2026, 6, 8, 15, 0), 5.0)]),
            # the 1h break at the end: 07:00-19:00 worked, 4h over
            (datetime(2026, 6, 9, 7, 0), datetime(2026, 6, 9, 20, 0), 1.0,
             [(datetime(2026, 6, 9, 15, 0), 4.0)]),
            # crosses midnight, the 0.5h break at the end: Wed 4h (< 8h) no excess; Thu 00:00-08:30,
            # 0.5h over the 8h
            (datetime(2026, 6, 10, 20, 0), datetime(2026, 6, 11, 9, 0), 0.5,
             [(datetime(2026, 6, 11, 8, 0), 0.5)]),
            # day off
            (datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0), 0.0,
             [(datetime(2026, 6, 13, 9, 0), 3.0)]),
        ]
        for check_in, check_out, break_duration, expected in cases:
            with self.subTest(check_in=check_in, break_duration=break_duration):
                att = self._create(check_in, check_out, break_duration=break_duration)
                outputs = self.env['hr.leave'].search([('attendance_id', '=', att.id), ('time_rule_id', '!=', False)],
                                                      order='date_from')
                self.assertEqual(len(outputs), len(expected))
                for output, (start, hours) in zip(outputs, expected):
                    self.assertAlmostEqual((output.date_from - start).total_seconds(), 0, delta=1)
                    self.assertAlmostEqual(self._hours(output), hours, delta=1e-3)
                    self.assertEqual(output.work_entry_type_id, self.ot_type)
                self.assertEqual((att.check_in, att.check_out, att.break_duration), (check_in, check_out, break_duration))

    def test_outputs_of_overtime_day(self):
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        output = att.related_leave_ids
        self.assertEqual(len(output), 1)
        self.assertEqual(att.related_leave_count, 1)
        self.assertEqual(output.time_rule_id, self.rule)
        self.assertEqual(output.work_entry_type_id, self.ot_type)
        self.assertEqual(output.attendance_id, att)
        self.assertEqual(output.state, 'validate')
        self.assertAlmostEqual(self._hours(output), 5.0, places=4)
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))

    def test_outputs_of_day_off_cover_whole_attendance(self):
        # Saturday: the whole attendance is excess, but it is not retyped nor replaced: the time off covers it
        att = self._create(datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))
        output = att.related_leave_ids
        self.assertEqual(len(output), 1)
        self.assertEqual(output.work_entry_type_id, self.ot_type)
        self.assertEqual((output.date_from, output.date_to), (att.check_in, att.check_out))
        self._assert_attendance_kept(att, datetime(2026, 6, 13, 9, 0), datetime(2026, 6, 13, 12, 0))

    def test_no_related_leave_without_excess(self):
        att = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 16, 0))
        self.assertFalse(att.related_leave_ids)
        self.assertEqual(att.related_leave_count, 0)

    def test_outputs_written_on_validation(self):
        self.env.company.attendance_validation = 'manual_validation'
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0), in_mode='kiosk', out_mode='kiosk')
        self.assertEqual(att.state, 'draft')
        self.assertFalse(self._outputs(self.employee), "a draft attendance has no output yet")
        att.action_validate()
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual(output.attendance_id, att)
        self.assertAlmostEqual(self._hours(output), 5.0, places=4)
        self._assert_attendance_kept(att, datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))

    def test_outputs_not_duplicated_on_rerun(self):
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(len(self._outputs(self.employee)), 1)
        # writing a trigger field re-runs the rules, which replace their outputs
        att.write({'break_duration': 0.0})
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual(output.attendance_id, att)
        self.assertAlmostEqual(self._hours(output), 5.0, places=4)
        self.assertEqual(att.related_leave_ids, output)

    def test_outputs_follow_moved_attendance(self):
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        # moved to Tuesday: the output of Monday is replaced by the one of Tuesday
        att.write({'check_in': datetime(2026, 6, 9, 7, 0), 'check_out': datetime(2026, 6, 9, 20, 0)})
        output = self._outputs(self.employee)
        self.assertEqual(len(output), 1)
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 9, 15, 0), datetime(2026, 6, 9, 20, 0)))
        # moved to a day still running: the output goes, the cron writes the new one
        with freeze_time('2026-06-10 21:00:00'):
            att.write({'check_in': datetime(2026, 6, 10, 7, 0), 'check_out': datetime(2026, 6, 10, 20, 0)})
        self.assertFalse(self._outputs(self.employee))
        with freeze_time('2026-06-11 01:00:00'):
            self.env['hr.attendance']._cron_process_day_time_rules()
        output = self._outputs(self.employee)
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 10, 15, 0), datetime(2026, 6, 10, 20, 0)))

    def test_outputs_follow_other_attendance_of_the_day(self):
        first = self._create(datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 12, 0))
        second = self._create(datetime(2026, 6, 8, 13, 0), datetime(2026, 6, 8, 20, 0))
        self.assertEqual(self._outputs(self.employee).attendance_id, second)
        # the first attendance moved to Tuesday, Monday has 7h: the overtime of the second one goes
        first.write({'check_in': datetime(2026, 6, 9, 8, 0), 'check_out': datetime(2026, 6, 9, 12, 0)})
        self.assertFalse(self._outputs(self.employee))

    def test_outputs_follow_version_of_attendance_day(self):
        # flexible from July: the June attendances keep the schedule of their version
        flexible = self.env['resource.calendar'].create({'name': 'Flexible', 'calendar_type': 'undefined'})
        self.employee.create_version({'date_version': date(2026, 7, 1), 'resource_calendar_id': flexible.id})
        att = self._create(datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0))
        output = self.env['hr.leave'].search([('attendance_id', '=', att.id)])
        self.assertEqual(output, self._outputs(self.employee))
        self.assertEqual((output.date_from, output.date_to), (datetime(2026, 6, 8, 15, 0), datetime(2026, 6, 8, 20, 0)))


@tagged('post_install', '-at_install', 'time_rule_pipeline')
class TestAttendanceCheckOutOutputs(TimeRuleOutputsCommon, HttpCase):
    """The time off written after a check-out from the systray and the kiosk. The day of the
    check-out is still running: its rules run from the daily cron, the day after."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'Split Check-Out Company'})
        cls.att_type = cls.env.ref('hr_work_entry.generic_work_entry_type_attendance')
        cls.ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Check-Out Test Overtime',
            'code': 'OT_CHECKOUT_TEST',
        })
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Check-Out Test)',
            'company_id': cls.company.id,
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [Command.link(cls.att_type.id)],
        })
        cls.user = cls.env['res.users'].create({
            'name': 'split_user',
            'login': 'split_user',
            'password': 'split_user',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        # company calendar: Mon-Fri, 8h a day
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Split Employee',
            'company_id': cls.company.id,
            'user_id': cls.user.id,
            'tz': 'UTC',
            'barcode': 'SPLIT123',
            'work_entry_source': 'attendance',
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
        self.authenticate('split_user', 'split_user')
        return self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})

    def _kiosk_check_out(self):
        return self.make_jsonrpc_request('/hr_attendance/attendance_barcode_scanned', {
            'token': self.company.attendance_kiosk_key,
            'barcode': 'SPLIT123',
        })

    def _run_daily_cron(self):
        """The day after the check-out, the daily cron evaluates the attendances of the day."""
        with freeze_time('2026-06-09 01:00:00'):
            self.env['hr.attendance']._cron_process_day_time_rules()

    def _assert_overtime_output(self, hours, start):
        outputs = self._outputs(self.employee)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(outputs.work_entry_type_id, self.ot_type)
        self.assertEqual(outputs.attendance_id, self.employee.last_attendance_id)
        self.assertEqual(outputs.date_from, start)
        self.assertAlmostEqual(self._hours(outputs), hours, places=4)

    @freeze_time('2026-06-08 17:00:00')  # Monday
    def test_systray_check_out_outputs(self):
        # within the tolerance, the day has no issue: it is reviewed, so evaluated, at check-out
        self.company.attendance_validation_tolerance = 60
        self._check_in(datetime(2026, 6, 8, 8, 0))
        self._systray_check_out()
        attendance = self.employee.last_attendance_id
        self.assertEqual(attendance.state, 'validated')
        # 9h for 8h scheduled; the day is still running: no output before the cron
        self.assertFalse(self._outputs(self.employee))
        self._run_daily_cron()
        self._assert_overtime_output(1.0, datetime(2026, 6, 8, 16, 0))
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (datetime(2026, 6, 8, 8, 0), datetime(2026, 6, 8, 17, 0)))
        self.assertEqual(self._attendances(self.employee), attendance)

    @freeze_time('2026-06-08 20:00:00')
    def test_systray_check_out_outputs_pending_validation(self):
        self.company.attendance_validation = 'manual_validation'
        self._check_in(datetime(2026, 6, 8, 7, 0))
        self._systray_check_out()
        attendance = self.employee.last_attendance_id
        self.assertEqual(attendance.state, 'draft')
        self.assertFalse(self._outputs(self.employee))
        self._run_daily_cron()
        self.assertFalse(self._outputs(self.employee), "a draft attendance is not evaluated before validation")
        # 13h for 8h scheduled once validated: the last 5h
        with freeze_time('2026-06-09 02:00:00'):
            attendance.action_validate()
        self._assert_overtime_output(5.0, datetime(2026, 6, 8, 15, 0))
        self.assertEqual((attendance.check_in, attendance.check_out),
                         (datetime(2026, 6, 8, 7, 0), datetime(2026, 6, 8, 20, 0)))
        self.assertEqual(self._attendances(self.employee), attendance)

    @freeze_time('2026-06-08 16:00:00')
    def test_systray_check_out_without_output(self):
        self._check_in(datetime(2026, 6, 8, 8, 0))
        self._systray_check_out()
        self.assertEqual(self.employee.attendance_state, 'checked_out')
        self._run_daily_cron()
        self.assertFalse(self._outputs(self.employee))

    @freeze_time('2026-06-08 08:00:00')
    def test_systray_check_in_creates_no_output(self):
        self._systray_check_out()
        self.assertEqual(self.employee.attendance_state, 'checked_in')
        self.assertFalse(self.employee.last_attendance_id.check_out)
        self.assertFalse(self._outputs(self.employee))

    @freeze_time('2026-06-08 17:00:00')
    def test_kiosk_check_out_outputs(self):
        self.company.attendance_validation_tolerance = 60
        self._check_in(datetime(2026, 6, 8, 8, 0))
        self._kiosk_check_out()
        self.assertFalse(self._outputs(self.employee))
        self._run_daily_cron()
        self._assert_overtime_output(1.0, datetime(2026, 6, 8, 16, 0))
        self.assertEqual(self._attendances(self.employee), self.employee.last_attendance_id)
