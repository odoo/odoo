# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestExpectedHours(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_40h, cls.calendar_mornings, cls.calendar_fully_flex = cls.env['resource.calendar'].create([{
            'name': 'Standard 40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': weekday, 'hour_from': hour, 'hour_to': hour + 4})
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
        }, {
            'name': 'Mornings 20h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': weekday, 'hour_from': 8, 'hour_to': 12})
                for weekday in ['0', '1', '2', '3', '4']
            ],
        }, {
            'name': 'Fully Flexible',
            'calendar_type': 'undefined',
            'attendance_ids': [],
        }])
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Expected Hours Employee',
            'tz': 'Europe/Brussels',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 1000,
            'resource_calendar_id': cls.calendar_40h.id,
        })
        cls.leave_type = cls.env['hr.work.entry.type'].create({
            'name': 'Expected Hours Time Off',
            'code': 'EXPECTEDHOURS',
            'count_as': 'absence',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'half_day',
        })

    def _create_leave(self, date_from, date_to, period=False):
        return self.env['hr.leave'].create({
            'employee_id': self.employee.id,
            'work_entry_type_id': self.leave_type.id,
            'request_date_from': date_from,
            'request_date_to': date_to,
            'request_date_from_period': period or 'am',
            'request_date_to_period': period or 'pm',
        })

    def test_expected_hours_per_day(self):
        # Monday 2 to Friday 6 March 2026: the last day of the range must be included
        self.assertEqual(self.employee.get_expected_hours('2026-03-02', '2026-03-06'), {
            '2026-03-02': 8.0,
            '2026-03-03': 8.0,
            '2026-03-04': 8.0,
            '2026-03-05': 8.0,
            '2026-03-06': 8.0,
        })
        # no attendance on the weekend
        self.assertEqual(self.employee.get_expected_hours('2026-03-07', '2026-03-08'), {})

    def test_expected_hours_with_leaves(self):
        self._create_leave(date(2026, 3, 3), date(2026, 3, 3))
        self._create_leave(date(2026, 3, 5), date(2026, 3, 5), period='am')
        expected_hours = self.employee.get_expected_hours('2026-03-02', '2026-03-06')
        self.assertEqual(expected_hours, {
            '2026-03-02': 8.0,
            '2026-03-04': 8.0,
            '2026-03-05': 4.0,
            '2026-03-06': 8.0,
        })

    def test_expected_hours_version_change(self):
        self.employee.create_version({
            'date_version': date(2026, 3, 9),
            'resource_calendar_id': self.calendar_mornings.id,
        })
        expected_hours = self.employee.get_expected_hours('2026-03-05', '2026-03-10')
        self.assertEqual(expected_hours, {
            '2026-03-05': 8.0,
            '2026-03-06': 8.0,
            '2026-03-09': 4.0,
            '2026-03-10': 4.0,
        })

    def test_expected_hours_fully_flexible(self):
        self.employee.resource_calendar_id = self.calendar_fully_flex
        self.assertEqual(self.employee.get_expected_hours('2026-03-02', '2026-03-06'), {})
