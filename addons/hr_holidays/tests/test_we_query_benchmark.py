# Part of Odoo. See LICENSE file for full copyright and licensing details.
# TEMPORARY BENCHMARK FILE — not meant to be committed.
import json
import logging
import os
from datetime import date, datetime

from odoo import models
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)

DUMP_DIR = '/tmp/we_bench'


@tagged('-standard', '-at_install', 'post_install', 'work_entry_bench')
class TestWorkEntryQueryBench(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        os.makedirs(DUMP_DIR, exist_ok=True)
        cls.company = cls.env.company
        cls.calendar_40h = cls.company.resource_calendar_id
        cls.calendar_35h = cls.env['resource.calendar'].create({
            'name': 'Bench 35h',
            'company_id': cls.company.id,
            'hours_per_day': 7.0,
        })
        cls.calendar_2w = cls.env['resource.calendar'].create({
            'name': 'Bench two weeks',
            'company_id': cls.company.id,
            'two_weeks_calendar': True,
        })
        cls.absence_type = cls.env['hr.work.entry.type'].create({
            'name': 'Bench Absence',
            'code': 'BENCHLEAVE',
            'count_as': 'absence',
        })
        cls.date_from = date(2026, 6, 1)
        cls.date_to = date(2026, 6, 30)

    @classmethod
    def _create_employees(cls, count, calendar, prefix, extra_version_vals=None):
        employees = cls.env['hr.employee'].create([{
            'name': f'{prefix} {i}',
            'company_id': cls.company.id,
            'tz': 'Europe/Brussels',
            'resource_calendar_id': calendar.id if calendar else False,
        } for i in range(count)])
        version_vals = {
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'contract_date_end': False,
            'resource_calendar_id': calendar.id if calendar else False,
        }
        if extra_version_vals:
            version_vals.update(extra_version_vals)
        employees.version_id.write(version_vals)
        return employees

    def _measure(self, employees, label):
        env = self.env
        env.flush_all()
        # Warmup run: fills registry-level caches (env.ref, field setup),
        # mirroring @warmup of the standard perf tests.
        employees.generate_work_entries(self.date_from, self.date_to)
        env.flush_all()
        env.invalidate_all()
        count_before = self.cr.sql_log_count
        vals = employees.generate_work_entries(self.date_from, self.date_to)
        env.flush_all()
        queries = self.cr.sql_log_count - count_before
        _logger.warning("WE-BENCH %s: queries=%d vals=%d", label, queries, len(vals))
        self._dump(vals, label)
        return vals

    def _dump(self, vals_list, label):
        def ser(v):
            if isinstance(v, models.BaseModel):
                # ids are not stable across runs (sequences keep advancing):
                # serialize stable human identifiers instead
                if v._name == 'hr.version':
                    return sorted(f'{ver.employee_id.name}@{ver.date_version}' for ver in v)
                return sorted(v.mapped('display_name'))
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            if isinstance(v, float):
                return round(v, 6)
            return v
        data = sorted(
            [{k: ser(v) for k, v in sorted(vals.items())} for vals in vals_list],
            key=lambda d: json.dumps(d, sort_keys=True),
        )
        with open(os.path.join(DUMP_DIR, f'{label}.json'), 'w') as f:
            json.dump(data, f, indent=1, sort_keys=True)

    def test_bench_01_simple_calendar(self):
        employees = self._create_employees(100, self.calendar_40h, 'Simple')
        self._measure(employees, 'simple_calendar_100emp_month')

    def test_bench_02_calendar_with_leaves(self):
        employees = self._create_employees(100, self.calendar_40h, 'Leave')
        # one 3-day personal absence per employee, staggered over the month
        self.env['resource.calendar.leaves'].create([{
            'name': f'Absence {i}',
            'calendar_id': self.calendar_40h.id,
            'resource_id': emp.resource_id.id,
            'company_id': self.company.id,
            'date_from': datetime(2026, 6, 1 + (i % 20), 6, 0),
            'date_to': datetime(2026, 6, 3 + (i % 20), 18, 0),
            'work_entry_type_id': self.absence_type.id,
        } for i, emp in enumerate(employees)])
        # one global day off for the whole calendar
        self.env['resource.calendar.leaves'].create({
            'name': 'Global day off',
            'calendar_id': self.calendar_40h.id,
            'company_id': self.company.id,
            'date_from': datetime(2026, 6, 24, 0, 0),
            'date_to': datetime(2026, 6, 24, 23, 59, 59),
            'work_entry_type_id': self.absence_type.id,
        })
        self._measure(employees, 'calendar_leaves_100emp_month')

    def test_bench_03_flexible(self):
        flexible = self._create_employees(
            30, None, 'Flex', {'hours_per_week': 30.0, 'hours_per_day': 6.0})
        fully_flexible = self._create_employees(
            20, None, 'FullFlex', {'hours_per_week': 0.0, 'hours_per_day': 0.0})
        employees = flexible | fully_flexible
        # a few absences for flexible employees
        self.env['resource.calendar.leaves'].create([{
            'name': f'Flex absence {i}',
            'resource_id': emp.resource_id.id,
            'company_id': self.company.id,
            'date_from': datetime(2026, 6, 8 + i, 6, 0),
            'date_to': datetime(2026, 6, 9 + i, 18, 0),
            'work_entry_type_id': self.absence_type.id,
        } for i, emp in enumerate(flexible[:10])])
        self._measure(employees, 'flexible_50emp_month')

    def test_bench_04_multi_calendar(self):
        emp40 = self._create_employees(30, self.calendar_40h, 'Cal40')
        emp35 = self._create_employees(30, self.calendar_35h, 'Cal35')
        emp2w = self._create_employees(30, self.calendar_2w, 'Cal2w')
        employees = emp40 | emp35 | emp2w
        self.env['resource.calendar.leaves'].create([{
            'name': f'Multi absence {i}',
            'calendar_id': emp.resource_calendar_id.id,
            'resource_id': emp.resource_id.id,
            'company_id': self.company.id,
            'date_from': datetime(2026, 6, 2 + (i % 15), 6, 0),
            'date_to': datetime(2026, 6, 4 + (i % 15), 18, 0),
            'work_entry_type_id': self.absence_type.id,
        } for i, emp in enumerate(employees[::3])])
        self._measure(employees, 'multi_calendar_90emp_month')
