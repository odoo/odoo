# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
import logging
import time

from odoo.tests.common import tagged, TransactionCase

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'hr_attendance_perf')
class TestHrTimeRulePerformance(TransactionCase):
    """
    Performance test for the time-rule pipeline.

    Setup: 100 employees, 3 contract versions each,
    one attendance per calendar day over a 2-month window.  All existing time
    rules are disabled so that setUpClass does not trigger rule evaluation;
    source leaves are produced by _sync_work_time_leave as attendances are
    created.  The measured operation is a full batch re-evaluation of those
    source leaves against a single daily-schedule overtime rule.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env['res.company'].create({'name': 'Flower Corporation', 'tz': 'Europe/Brussels'})
        cls.env.user.company_id = cls.company

        cls.calendar_38h = cls.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'company_id': False,
            'hours_per_day': 7.6,
            'attendance_ids': [
                (0, 0, {'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6}),
                (0, 0, {'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
                (0, 0, {'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6}),
            ],
        })
        cls.company.resource_calendar_id = cls.calendar_38h

        # silence all pre-existing time rules
        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.overtime_type = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')
        cls.att_type = cls.company._get_default_attendance_work_entry_type()

        cls.time_rule = cls.env['hr.time.rule'].create({
            'name': 'Daily schedule overtime',
            'working_hours_mode': 'schedule_day',
            'work_entry_type_id': cls.overtime_type.id,
            'condition_work_entry_type_ids': [cls.att_type.id],
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
            'attendance_based': True,
            'company_id': cls.company.id,
        } for i in range(100)])
        for employee in employees:
            employee.create_version({'date_version': date.today() - relativedelta(months=1, days=15), 'wage': 5500})
            employee.create_version({'date_version': date.today() - relativedelta(months=1), 'wage': 6000})

        cls.employees = employees
        vals = []
        for employee in employees:
            for day in rrule(DAILY, dtstart=date.today() - relativedelta(months=2), until=date.today()):
                vals.append({
                    'employee_id': employee.id,
                    'check_in': day.replace(hour=8, minute=0),
                    'check_out': day.replace(hour=17, minute=36),
                })
        cls.attendances = cls.env['hr.attendance'].with_context(skip_time_rules=True).create(vals)

    def test_reprocess_time_rules(self):
        start = date.today() - relativedelta(months=2)
        end = date.today()
        affected = [(emp, start, end) for emp in self.employees]

        t0 = time.time()
        with self.assertQueryCount(367):
            self.env['hr.leave']._process_time_rules_for(affected)
        t1 = time.time()

        _logger.info(
            "Reprocessed time rules for %s attendance records across %s employees in %.2f seconds.",
            len(self.attendances.ids),
            len(self.employees),
            t1 - t0,
        )
