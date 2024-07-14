# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.tests.common import tagged, TransactionCase


@tagged('-at_install', 'post_install')
class TestHrAttendanceGantt(TransactionCase):
    def test_gantt_progress_bar(self):
        contracts_installed = 'hr.contract' in self.env
        calendar_8 = self.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 8.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 17, 'day_period': 'afternoon'}),
            ]
        })

        calendar_10 = self.env['resource.calendar'].create({
            'name': 'Calendar 1',
            'tz': 'UTC',
            'hours_per_day': 10.0,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 9, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 19, 'day_period': 'afternoon'}),
            ]
        })

        calendar_12 = self.env['resource.calendar'].create({
            'name': 'Calendar 1',
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
                    'name': 'Johnny Contract 8 hours',
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

        interval_1 = self.env['hr.attendance'].gantt_progress_bar(['employee_id'],
                                                                  {'employee_id': [no_contract_emp.id, contract_emp.id]},
                                                                  date(2024, 1, 8),
                                                                  date(2024, 1, 14))

        self.assertEqual(interval_1["employee_id"][no_contract_emp.id]['max_value'], 8)

        if contracts_installed:
            self.assertEqual(interval_1["employee_id"][contract_emp.id]['max_value'], 8)
        else:
            self.assertEqual(interval_1["employee_id"][contract_emp.id]['max_value'], 10)

        # Second Interval in March
        # No contract should have 8 hours
        # Contract employee should have 10 hours if contracts is not installed
        # Contract employee should have 12 hours if contracts is installed

        interval_2 = self.env['hr.attendance'].gantt_progress_bar(['employee_id'],
                                                                  {'employee_id': [no_contract_emp.id, contract_emp.id]},
                                                                  date(2024, 3, 4),
                                                                  date(2024, 3, 10))

        self.assertEqual(interval_2["employee_id"][no_contract_emp.id]['max_value'], 8)

        if contracts_installed:
            self.assertEqual(interval_2["employee_id"][contract_emp.id]['max_value'], 12)
        else:
            self.assertEqual(interval_2["employee_id"][contract_emp.id]['max_value'], 10)
