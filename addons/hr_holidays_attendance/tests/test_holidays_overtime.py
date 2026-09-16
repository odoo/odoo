# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import Command
from odoo.tests import new_test_user, tagged
from odoo.tests.common import HttpCase, TransactionCase


class HrHolidaysOvertimeCommon(TransactionCase):
    """Shared setup for overtime time-rule tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'name': 'Standard 40h/week',
            'attendance_ids': [
                Command.create({'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.tz = 'UTC'

        cls.att_wet = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_wet
        cls.overtime_wet = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')

        # deactivate all data-file rules so tests are self-contained
        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.user = new_test_user(
            cls.env,
            login='overtime_user',
            groups='base.group_user,hr_holidays.group_hr_holidays_employee',
        )
        cls.employee = cls.env['hr.employee'].create({
            'name': 'OT Test Employee',
            'user_id': cls.user.id,
            'tz': 'UTC',
            'attendance_based': True,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })

        # daily schedule rule — applies all hours, all days (timing 0-24, all weekdays True by default)
        cls.daily_rule = cls.env['hr.time.rule'].create({
            'name': 'Daily OT Rule',
            'working_hours_mode': 'schedule_day',
            'work_entry_type_id': cls.overtime_wet.id,
            'condition_work_entry_type_ids': [Command.set([cls.att_wet.id])],
        })

    def _output_atts(self, employee, rule=None):
        domain = [
            ('employee_id', '=', employee.id),
            ('time_rule_id', '!=', False),
        ]
        if rule:
            domain.append(('time_rule_id', '=', rule.id))
        return self.env['hr.attendance'].search(domain)

    def _output_hours(self, atts):
        return sum(a.worked_hours for a in atts)

    def new_attendance(self, check_in, check_out):
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        })


@tagged('-at_install', 'post_install', 'holidays_attendance')
class TestHolidaysOvertimeRules(HrHolidaysOvertimeCommon):

    def test_weekly_overtime_schedule_employee(self):
        """Employee with a 40h/week schedule who works 50h in one week earns 10h overtime.

        Mon 8h, Tue 10h, Wed 5h, Thu 15h, Fri 12h = 50h total; schedule = 40h → 10h excess.
        """
        flex_emp = self.env['hr.employee'].create({
            'name': 'Flex OT Employee',
            'tz': 'UTC',
            'attendance_based': True,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
        })
        self.daily_rule.active = False
        weekly_rule = self.env['hr.time.rule'].create({
            'name': 'Weekly Schedule Rule',
            'working_hours_mode': 'schedule_week',
            'work_entry_type_id': self.overtime_wet.id,
            'condition_work_entry_type_ids': [Command.set([self.att_wet.id])],
        })
        # week of 2026-05-04 (Mon-Fri): total = 8+10+5+15+12 = 50h, schedule = 40h
        for check_in, check_out in [
            (datetime(2026, 5, 4, 8, 15), datetime(2026, 5, 4, 16, 15)),   # Mon 8h
            (datetime(2026, 5, 5, 8, 15), datetime(2026, 5, 5, 18, 15)),   # Tue 10h
            (datetime(2026, 5, 6, 8, 15), datetime(2026, 5, 6, 13, 15)),   # Wed 5h
            (datetime(2026, 5, 7, 8, 15), datetime(2026, 5, 7, 23, 15)),   # Thu 15h
            (datetime(2026, 5, 8, 8, 15), datetime(2026, 5, 8, 20, 15)),   # Fri 12h
        ]:
            self.env['hr.attendance'].create({
                'employee_id': flex_emp.id,
                'check_in': check_in,
                'check_out': check_out,
            })

        output_atts = self._output_atts(flex_emp, weekly_rule)
        total_hours = self._output_hours(output_atts)
        self.assertAlmostEqual(total_hours, 10.0, places=1,
                               msg="50h worked - 40h scheduled = 10h weekly overtime")

    def test_overtime_timing_adjacent_intervals(self):
        """Adjacent timing rules must not merge into one output attendance.

        Daytime rule:   17:00-21:00 (4h window)
        Nighttime rule: 21:00-24:00 (3h window)
        Attendance on a Monday 17:00-23:59:59

        Expected: two output attendances of ~4h and ~3h respectively.
        """
        self.daily_rule.active = False

        daytime_wet = self.env['hr.work.entry.type'].create({
            'name': 'Daytime OT', 'code': 'OTEST_DAY', 'requires_allocation': False,
        })
        nighttime_wet = self.env['hr.work.entry.type'].create({
            'name': 'Nighttime OT', 'code': 'OTEST_NIGHT', 'requires_allocation': False,
        })
        daytime_rule = self.env['hr.time.rule'].create({
            'name': 'Daytime',
            'working_hours_mode': 'schedule_day',
            'timing_start': 17.0,
            'timing_stop': 21.0,
            'work_entry_type_id': daytime_wet.id,
            'condition_work_entry_type_ids': [Command.set([self.att_wet.id])],
        })
        nighttime_rule = self.env['hr.time.rule'].create({
            'name': 'Nighttime',
            'working_hours_mode': 'schedule_day',
            'timing_start': 21.0,
            'timing_stop': 24.0,
            'work_entry_type_id': nighttime_wet.id,
            'condition_work_entry_type_ids': [Command.set([self.att_wet.id])],
        })
        # Monday 17:00-23:59:59 UTC; schedule has 0h after 17:00 → all hours are OT
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 1, 4, 17, 0, 0),
            'check_out': datetime(2021, 1, 4, 23, 59, 59),
        })

        daytime_atts = self._output_atts(self.employee, rule=daytime_rule)
        nighttime_atts = self._output_atts(self.employee, rule=nighttime_rule)

        self.assertEqual(len(daytime_atts), 1,
                         "Exactly one daytime output attendance should be created.")
        self.assertEqual(len(nighttime_atts), 1,
                         "Exactly one nighttime output attendance should be created.")
        self.assertAlmostEqual(self._output_hours(daytime_atts), 4.0, places=2,
                               msg="Daytime OT window 17:00-21:00 = 4h")
        self.assertAlmostEqual(self._output_hours(nighttime_atts), 3.0, places=2,
                               msg="Nighttime OT window 21:00-23:59:59 ≈ 3h")


@tagged('-at_install', 'post_install', 'holidays_attendance')
class TestHolidaysOvertimeKiosk(HrHolidaysOvertimeCommon, HttpCase):

    def test_employee_kiosk_total_overtime(self):
        """Kiosk endpoint reports total_overtime = output attendance hours from time rules.

        Two weekend attendances of 9h each = 18h of overtime output (schedule has 0h on Sat/Sun).
        """
        # Jan 2 (Sat) and Jan 3 (Sun) 2021 — 0h scheduled → all hours become overtime output
        self.new_attendance(
            check_in=datetime(2021, 1, 2, 8),
            check_out=datetime(2021, 1, 2, 17),
        )
        self.new_attendance(
            check_in=datetime(2021, 1, 3, 8),
            check_out=datetime(2021, 1, 3, 17),
        )
        self.assertAlmostEqual(self.employee.total_overtime, 18, places=1,
                               msg="9h × 2 weekend days = 18h overtime")

        token = self.employee.company_id.attendance_kiosk_key
        response = self.make_jsonrpc_request(
            '/hr_attendance/attendance_employee_data',
            {'token': token, 'employee_id': self.employee.id},
        )
        self.assertAlmostEqual(
            response.get('total_overtime'),
            18.0,
            places=1,
            msg="Kiosk should show total_overtime matching output attendance hours",
        )
<<<<<<< 57a4e5209ef744cd34c634bbfe16b4e99925bac4
||||||| ac816add8c899d5bbd20fdbc6f546c961544b74c

    def test_absence_management_with_timeoff(self):
        self.company.write({
            'absence_management': True,
        })
        self.employee.contract_date_start = datetime(2026, 1, 1)
        self.env.user.tz = 'UTC'
        self.employee.tz = 'UTC'
        self.employee.ruleset_id = self.ref('hr_attendance.hr_attendance_default_ruleset')

        leave = self.env['hr.leave'].create({
            'name': 'Vacation Yippie',
            'employee_id': self.employee.id,
            'work_entry_type_id': self.regular_leave_type.id,
            'request_date_from': datetime(2026, 1, 13),
            'request_date_to': datetime(2026, 1, 13),
        })
        leave.action_approve()
        with freeze_time('2026-01-14'):
            self.env['hr.attendance']._cron_absence_detection()
        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', '2026-01-13'),
        ]), 0)

        with freeze_time('2026-01-15'):
            self.env['hr.attendance']._cron_absence_detection()
        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', '2026-01-14'),
        ]), 1)

    def test_timeoff_after_absence_management(self):
        """
        Test that when an employee creates a leave covering an autogenerated
        absence attendance (created at 12:00 AM), the negative extra hours
        are correctly reset to 0.
        """
        self.company.write({
            'absence_management': True,
        })
        self.employee.contract_date_start = datetime(2026, 1, 1)
        self.env.user.tz = 'Europe/Brussels'
        self.employee.tz = 'Europe/Brussels'
        self.employee.ruleset_id = self.env.ref('hr_attendance.hr_attendance_default_ruleset')

        with freeze_time('2026-01-14'):
            self.env['hr.attendance']._cron_absence_detection()

        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', '2026-01-12'),
        ]), 1)
        self.assertAlmostEqual(self.employee.total_overtime, -8.0, 2)

        leave = self.env['hr.leave'].create({
            'name': 'Vacation Yippie',
            'employee_id': self.employee.id,
            'work_entry_type_id': self.regular_leave_type.id,
            'request_date_from': datetime(2026, 1, 13),
            'request_date_to': datetime(2026, 1, 13),
        })
        leave.action_approve()

        self.assertAlmostEqual(self.employee.total_overtime, 0.0, 2)
=======

    def test_timing_leave_overtime_without_break(self):
        """ Ensure that the scheduled break is not counted as extra hours when the employee works while off. """
        ruleset = self.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset employee is off',
            'company_id': self.company.id,
            'rule_ids': [
                Command.create({
                    'name': 'Rule employee is off',
                    'base_off': 'timing',
                    'timing_type': 'leave',
                }),
            ],
        })
        self.employee.ruleset_id = ruleset

        leave = self.env['hr.leave'].create({
            'name': 'Vacation Yippie',
            'employee_id': self.employee.id,
            'work_entry_type_id': self.regular_leave_type.id,
            'request_date_from': datetime(2026, 1, 13),
            'request_date_to': datetime(2026, 1, 13),
        })
        leave.action_approve()

        # The employee works the whole shift, the one hour break included.
        self.new_attendance(check_in=datetime(2026, 1, 13, 8), check_out=datetime(2026, 1, 13, 17))
        # Only the 8 scheduled work hours are extra hours, the break is not worked.
        self.assertEqual(self.employee.total_overtime, 8, 'The break should not be counted as extra hours.')

    def test_absence_management_with_timeoff(self):
        self.company.write({
            'absence_management': True,
        })
        self.employee.contract_date_start = datetime(2026, 1, 1)
        self.env.user.tz = 'UTC'
        self.employee.tz = 'UTC'
        self.employee.ruleset_id = self.ref('hr_attendance.hr_attendance_default_ruleset')

        leave = self.env['hr.leave'].create({
            'name': 'Vacation Yippie',
            'employee_id': self.employee.id,
            'work_entry_type_id': self.regular_leave_type.id,
            'request_date_from': datetime(2026, 1, 13),
            'request_date_to': datetime(2026, 1, 13),
        })
        leave.action_approve()
        with freeze_time('2026-01-14'):
            self.env['hr.attendance']._cron_absence_detection()
        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', '2026-01-13'),
        ]), 0)

        with freeze_time('2026-01-15'):
            self.env['hr.attendance']._cron_absence_detection()
        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '=', '2026-01-14'),
        ]), 1)

    def test_timeoff_after_absence_management(self):
        """
        Test that when an employee creates a leave covering an autogenerated
        absence attendance (created at 12:00 AM), the negative extra hours
        are correctly reset to 0.
        """
        self.company.write({
            'absence_management': True,
        })
        self.employee.contract_date_start = datetime(2026, 1, 1)
        self.env.user.tz = 'Europe/Brussels'
        self.employee.tz = 'Europe/Brussels'
        self.employee.ruleset_id = self.env.ref('hr_attendance.hr_attendance_default_ruleset')

        with freeze_time('2026-01-14'):
            self.env['hr.attendance']._cron_absence_detection()

        self.assertEqual(self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.employee.id),
            ('check_in', '>=', '2026-01-12'),
        ]), 1)
        self.assertAlmostEqual(self.employee.total_overtime, -8.0, 2)

        leave = self.env['hr.leave'].create({
            'name': 'Vacation Yippie',
            'employee_id': self.employee.id,
            'work_entry_type_id': self.regular_leave_type.id,
            'request_date_from': datetime(2026, 1, 13),
            'request_date_to': datetime(2026, 1, 13),
        })
        leave.action_approve()

        self.assertAlmostEqual(self.employee.total_overtime, 0.0, 2)
>>>>>>> 530bc0362a1b7d89b160f39157b72630def5c9d9
