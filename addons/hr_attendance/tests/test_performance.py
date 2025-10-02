# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
import logging
import time

from odoo import Command
from odoo.tests.common import tagged
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'hr_attendance_perf')
class TestHrAttendancePerformance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id = cls.env['res.company'].create({'name': 'Flower Corporation', 'tz': 'Europe/Brussels'})
        cls.calendar_38h = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'company_id': False,
            'hours_per_day': 7.6,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6})
            ],
        })

        cls.ruleset = cls.env['hr.attendance.overtime.ruleset'].create({
            'name': 'Ruleset schedule quantity',
            'rule_ids': [
                Command.create({
                    'name': 'Rule schedule quantity',
                    'base_off': 'quantity',
                    'expected_hours_from_contract': True,
                    'quantity_period': 'day',
                }),
                ],
        })

        employees = cls.env['hr.employee'].create([{
            'name': f'Employee {i}',
            'sex': 'male',
            'birthday': '1982-08-01',
            'country_id': cls.env.ref('base.us').id,
            'wage': 5000.0,
            'date_version': date.today() - relativedelta(months=2),
            'contract_date_start': date.today() - relativedelta(months=2),
            'contract_date_end': False,
            'resource_calendar_id': cls.calendar_38h.id,
            'ruleset_id': cls.ruleset.id,
        } for i in range(100)])
        for employee in employees:
            employee.create_version({'date_version': date.today() - relativedelta(months=1, days=15), 'wage': 5500})
            employee.create_version({'date_version': date.today() - relativedelta(months=1), 'wage': 6000})

        vals = []
        for employee in employees:
            for day in rrule(DAILY, dtstart=date.today() - relativedelta(months=2), until=date.today()):
                vals.append({
                    'employee_id': employee.id,
                    'check_in': day.replace(hour=8, minute=0),
                    'check_out': day.replace(hour=17, minute=36),
                })
        cls.attendances = cls.env['hr.attendance'].create(vals)

    def test_regenerate_overtime_line(self):
        t0 = time.time()
        with self.assertQueryCount(1700):
            self.ruleset.action_regenerate_overtimes()
        t1 = time.time()
        _logger.info("Regenerated overtime for %s hr.attendance records in %s seconds.",
            len(self.attendances.ids), t1 - t0)
