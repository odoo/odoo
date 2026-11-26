# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestAttendanceBreakRuleTimeOff(TransactionCase):
    """The break raised by a break rule is left out of the time off of the attendance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['hr.time.rule'].search([]).write({'active': False})
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Flexible Employee',
            'tz': 'UTC',
            'work_entry_source': 'attendance',
            'resource_calendar_id': cls.env['resource.calendar'].create({
                'name': 'Undefined Calendar',
                'calendar_type': 'undefined',
            }).id,
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
        })
        cls.env['hr.attendance.break.rule'].create({
            'name': 'Legal Breaks',
            'line_ids': [Command.create({'work_hours': 6, 'break_hours': 0.5})],
        })

    def _create(self, check_in, check_out, **vals):
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
            **vals,
        })

    def _time_off(self, attendance):
        return self.env['hr.leave'].search([('attendance_id', '=', attendance.id)], order='date_from')

    def test_raised_break_not_in_the_time_off(self):
        """8:00-15:00 without break: the break is raised to 30 minutes, the time off ends at 14:30, nothing covers the
        break."""
        attendance = self._create(datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 15))
        self.assertRecordValues(self._time_off(attendance), [
            {'date_from': datetime(2026, 6, 9, 8), 'date_to': datetime(2026, 6, 9, 14, 30)},
        ])

    def test_time_off_follows_the_break(self):
        """A later check out raises the break again, a longer break shortens the time off."""
        attendance = self._create(datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 15))
        attendance.check_out = datetime(2026, 6, 9, 16)
        self.assertRecordValues(self._time_off(attendance), [
            {'date_from': datetime(2026, 6, 9, 8), 'date_to': datetime(2026, 6, 9, 15, 30)},
        ])
        attendance.break_duration = 1.5
        self.assertRecordValues(self._time_off(attendance), [
            {'date_from': datetime(2026, 6, 9, 8), 'date_to': datetime(2026, 6, 9, 14, 30)},
        ])

    def test_scheduled_employee_break_at_the_end(self):
        """On a schedule (8:00-12:00, 13:00-17:00), 8:00-17:00 without break: the break is raised to 30 minutes and
        taken at the end, so 8h30 worked and the overtime is 16:00-16:30."""
        overtime_type = self.env['hr.work.entry.type'].create({'name': 'Overtime', 'code': 'BREAK_RULE_OT_TEST'})
        self.env['hr.time.rule'].create({
            'name': 'Overtime',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': overtime_type.id,
        })
        self.employee.resource_calendar_id = self.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                Command.create({'dayofweek': weekday, 'hour_from': hour, 'hour_to': hour + 4})
                for weekday in '01234'
                for hour in (8, 13)
            ],
        })
        attendance = self._create(datetime(2026, 6, 9, 8), datetime(2026, 6, 9, 17))
        self.assertRecordValues(self._time_off(attendance), [
            {'date_from': datetime(2026, 6, 9, 16), 'date_to': datetime(2026, 6, 9, 16, 30), 'work_entry_type_id': overtime_type.id},
        ])
