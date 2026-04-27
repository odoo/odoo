# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged, TransactionCase
from pytz import utc


@tagged('-at_install', 'post_install')
class TestHrAttendanceGantt(TransactionCase):
    def test_gantt_progress_bar(self):
        contracts_installed = 'hr.contract' in self.env
        calendar_8 = self.env['resource.calendar'].create({
            'name': 'Calendar 8h',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })

        calendar_10 = self.env['resource.calendar'].create({
            'name': 'Calendar 10h',
            'tz': 'UTC',
            'hours_per_day': 10.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 19, 'day_period': 'afternoon'}),
            ]
        })

        calendar_12 = self.env['resource.calendar'].create({
            'name': 'Calendar 12h',
            'tz': 'UTC',
            'hours_per_day': 12.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 21, 'day_period': 'afternoon'}),
            ]
        })

        no_contract_emp = self.env['hr.employee'].create({
            'name': "Johnny NoContract",
            'resource_calendar_id': calendar_8.id
        })

        contract_emp = self.env['hr.employee'].create({
            'name': "Johhny Contract",
            'resource_calendar_id': calendar_10.id
        })

        if contracts_installed:
            self.env['hr.contract'].create([
                {
                    'name': 'Johnny Contract 8 hours',
                    'employee_id': contract_emp.id,
                    'date_start': date(2024, 1, 1),
                    'date_end': date(2024, 2, 29),
                    'resource_calendar_id': calendar_8.id,
                    'wage': 10,
                    'state': 'close'
                },
                {
                    'name': 'Johnny Contract 12 hours',
                    'employee_id': contract_emp.id,
                    'date_start': date(2024, 3, 1),
                    'resource_calendar_id': calendar_12.id,
                    'wage': 10,
                    'state': 'open'
                }
            ])

        # First Interval in January
        # No contract should have 8 hours
        # Contract should have 10 hours if contracts is not installed
        # Contract should have 8 hours if contracts is installed

        interval_1 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [no_contract_emp.id, contract_emp.id],
                                                                  datetime(2024, 1, 8),
                                                                  datetime(2024, 1, 14))

        self.assertEqual(interval_1[no_contract_emp.id]['max_value'], 8)

        if contracts_installed:
            self.assertEqual(interval_1[contract_emp.id]['max_value'], 8)
        else:
            self.assertEqual(interval_1[contract_emp.id]['max_value'], 10)

        # Second Interval in March
        # No contract should have 8 hours
        # Contract employee should have 10 hours if contracts is not installed
        # Contract employee should have 12 hours if contracts is installed

        interval_2 = self.env['hr.attendance']._gantt_progress_bar('employee_id',
                                                                  [no_contract_emp.id, contract_emp.id],
                                                                  datetime(2024, 3, 4),
                                                                  datetime(2024, 3, 10))

        self.assertEqual(interval_2[no_contract_emp.id]['max_value'], 8)

        if contracts_installed:
            self.assertEqual(interval_2[contract_emp.id]['max_value'], 12)
        else:
            self.assertEqual(interval_2[contract_emp.id]['max_value'], 10)

    def test_gantt_progress_with_flexible_employees(self):
        flexible_calendar, calendar = self.env['resource.calendar'].create([
            {
                'name': 'Calendar 8h',
                'tz': 'UTC',
                'full_time_required_hours': 8.0,
                'hours_per_day': 8.0,
                'flexible_hours': True,
            }, {
                'name': 'Calendar 8h',
                'tz': 'UTC',
                'full_time_required_hours': 8.0,
                'hours_per_day': 8.0,
                'attendance_ids': [
                    (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
                ],
            },
        ])

        emp1, emp2 = self.env['hr.employee'].create([
            {'name': 'freelance1', 'employee_type': 'freelance', 'resource_calendar_id': flexible_calendar.id},
            {'name': 'freelance2', 'employee_type': 'freelance', 'resource_calendar_id': calendar.id},
        ])
        self.assertTrue(emp1.is_flexible)
        self.assertFalse(emp2.is_flexible)
        calendar.flexible_hours = True  # emp2 should now have a flexible hours as well

        interval = self.env['hr.attendance']._gantt_progress_bar(
            'employee_id',
            [emp1.id, emp2.id],
            datetime(2024, 1, 8),
            datetime(2024, 1, 15),
        )

        self.assertEqual(interval[emp1.id]['max_value'], 8)
        self.assertEqual(interval[emp2.id]['max_value'], 8)

    def test_gantt_rows_exclude_archived_amployee(self):
        emp1 = self.env['hr.employee'].create({'name': 'Employee 1'})
        emp2 = self.env['hr.employee'].create({'name': 'Employee 2'})
        gantt_context = {
            'gantt_start_date': '2026-02-10',
            'group_by': ['employee_id'],
            'user_domain': [],
        }
        gantt_domain = [
            '&',
            ['check_in', '<', '2026-02-10 23:00:00'],
            '|',
            '&',
            ['check_in', '<', '2026-02-10 12:00:30'],
            ['check_out', '=', False],
            ['check_out', '>', '2026-02-09 23:00:00']
        ]
        gantt_read_specification = {
            'display_name': {},
            'check_in': {},
            'check_out': {},
            'employee_id': {
            'fields': {
                'display_name': {}
            }
            },
            'color': {},
            'overtime_progress': {}
        }
        self.env['hr.attendance'].create({
            'employee_id': emp1.id,
            'check_in': datetime(2026, 1, 9, 8, 0, 0),
            'check_out': datetime(2026, 1, 9, 17, 0, 0)
        })
        self.env['hr.attendance'].create({
            'employee_id': emp2.id,
            'check_in': datetime(2026, 1, 9, 8, 0, 0),
            'check_out': datetime(2026, 1, 9, 17, 0, 0)
        })
        emp2.active = False
        gaant_data = self.env['hr.attendance'].with_context(**gantt_context).get_gantt_data(
            domain=gantt_domain,
            groupby=['employee_id'],
            read_specification=gantt_read_specification,
            start_date='2026-02-10',
            stop_date='2026-03-10',
            unavailability_fields=['employee_id'],
            scale='day',
        )['groups']
        rows = [employee['employee_id'][0] for employee in gaant_data]
        self.assertIn(emp1.id, rows)
        self.assertNotIn(emp2.id, rows)

    def test_attendance_gantt_unavailabilities_flexible_employee(self):
        employee = self.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
        })

        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'Flex Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 8,
            'full_time_required_hours': 40,
            'attendance_ids': [],
        })
        employee.resource_id.calendar_id = flexible_calendar

        if (Contract := self.env.get('hr.contract')) is not None:
            Contract.create({
                'name': 'Test Contract',
                'employee_id': employee.id,
                'state': 'open',
                'date_start': datetime(2018, 1, 1),
                'date_end': datetime(2020, 1, 1),
                'resource_calendar_id': flexible_calendar.id,
                'wage': 1000,
            })

        unavailabilities = self.env['hr.attendance']._gantt_unavailability(
            'employee_id',
            [employee.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'week',
        )
        self.assertEqual(unavailabilities[employee.id], [])

        public_holiday = self.env['resource.calendar.leaves'].create({
            'name': 'Public Holiday',
            'date_from': datetime(2019, 1, 5, 0, 0, 0),
            'date_to': datetime(2019, 1, 5, 23, 59, 59),
        })

        unavailabilities = self.env['hr.attendance']._gantt_unavailability(
            'employee_id',
            [employee.id],
            datetime(2019, 1, 1),
            datetime(2019, 1, 7),
            'week',
        )
        self.assertEqual(unavailabilities[employee.id][0]['start'], public_holiday.date_from.astimezone(utc))
        self.assertEqual(unavailabilities[employee.id][0]['stop'], public_holiday.date_to.astimezone(utc))
