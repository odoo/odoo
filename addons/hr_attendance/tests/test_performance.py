import logging
import time
from datetime import date

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import Command, fields
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


# A FIXED anchor, not `date.today()`. The fixture spans two months of calendar
# days, so against a moving anchor both the number of attendances and their
# weekday composition change every day -- and so does the query count a budget
# is supposed to pin. 2025-09-02 gives 63 days (30 + 31 + 2) and therefore
# 6,300 attendances over the 100 employees, whatever day this runs.
_ANCHOR = date(2025, 9, 2)
# TWO NUMBERS, BOTH EXACT, BECAUSE THE BUDGET IS A FUNCTION OF THE INSTALLED
# MODULE SET AND NOT ONLY OF THIS MODULE'S CODE. `hr_work_entry_attendance`
# overrides `hr.attendance._get_employee_calendar()` to prefer a contract's own
# schedule, and that override costs exactly one query on this path -- measured
# by installing it into a database that had just read 258 and re-running: 259.
#
# A single budget of 259 was what this test carried first, taken on a database
# that happened to have the enterprise module on it, and it printed
# `Query count less than expected: 258 < 259` on every clean run -- which is
# the exact defect this test's own comment was written to describe.
_REGENERATION_QUERIES = 258
_REGENERATION_QUERIES_WITH_WORK_ENTRIES = 259


@tagged("post_install", "-at_install", "hr_attendance_perf")
class TestHrAttendancePerformance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id = cls.env["res.company"].create(
            {"name": "Flower Corporation"}
        )
        cls.calendar_38h = cls.env["resource.calendar"].create(
            {
                "name": "Standard 38 hours/week",
                "tz": "Europe/Brussels",
                "company_id": False,
                "hours_per_day": 7.6,
                "attendance_ids": [
                    (5, 0, 0),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Morning",
                            "dayofweek": "0",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Lunch",
                            "dayofweek": "0",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Monday Afternoon",
                            "dayofweek": "0",
                            "hour_from": 13,
                            "hour_to": 16.6,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Morning",
                            "dayofweek": "1",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Lunch",
                            "dayofweek": "1",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Tuesday Afternoon",
                            "dayofweek": "1",
                            "hour_from": 13,
                            "hour_to": 16.6,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Morning",
                            "dayofweek": "2",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Lunch",
                            "dayofweek": "2",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Wednesday Afternoon",
                            "dayofweek": "2",
                            "hour_from": 13,
                            "hour_to": 16.6,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Morning",
                            "dayofweek": "3",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Lunch",
                            "dayofweek": "3",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Thursday Afternoon",
                            "dayofweek": "3",
                            "hour_from": 13,
                            "hour_to": 16.6,
                            "day_period": "afternoon",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Morning",
                            "dayofweek": "4",
                            "hour_from": 8,
                            "hour_to": 12,
                            "day_period": "morning",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Lunch",
                            "dayofweek": "4",
                            "hour_from": 12,
                            "hour_to": 13,
                            "day_period": "lunch",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Friday Afternoon",
                            "dayofweek": "4",
                            "hour_from": 13,
                            "hour_to": 16.6,
                            "day_period": "afternoon",
                        },
                    ),
                ],
            }
        )

        cls.ruleset = cls.env["hr.attendance.overtime.ruleset"].create(
            {
                "name": "Ruleset schedule quantity",
                "rule_ids": [
                    Command.create(
                        {
                            "name": "Rule schedule quantity",
                            "base_off": "quantity",
                            "expected_hours_from_contract": True,
                            "quantity_period": "day",
                        }
                    ),
                ],
            }
        )

        employees = cls.env["hr.employee"].create(
            [
                {
                    "name": f"Employee {i}",
                    "sex": "male",
                    "birthday": "1982-08-01",
                    "country_id": cls.env.ref("base.us").id,
                    "wage": 5000.0,
                    "date_version": _ANCHOR - relativedelta(months=2),
                    "contract_date_start": _ANCHOR - relativedelta(months=2),
                    "contract_date_end": False,
                    "resource_calendar_id": cls.calendar_38h.id,
                    "ruleset_id": cls.ruleset.id,
                }
                for i in range(100)
            ]
        )
        for employee in employees:
            employee.create_version(
                {
                    "date_version": _ANCHOR - relativedelta(months=1, days=15),
                    "wage": 5500,
                }
            )
            employee.create_version(
                {"date_version": _ANCHOR - relativedelta(months=1), "wage": 6000}
            )

        vals = []
        for employee in employees:
            vals.extend(
                {
                    "employee_id": employee.id,
                    "check_in": day.replace(hour=8, minute=0),
                    "check_out": day.replace(hour=17, minute=36),
                }
                for day in rrule(
                    DAILY,
                    dtstart=_ANCHOR - relativedelta(months=2),
                    until=_ANCHOR,
                )
            )
        cls.attendances = cls.env["hr.attendance"].create(vals)

    def test_regenerate_overtime_line(self):
        # The budget is the measurement, with no headroom. It was 1,700 once --
        # six times the real cost -- and `assertQueryCount` only LOGS when the
        # count comes in under budget, so that gap was reported on every run
        # and failed nothing: a regeneration that started issuing a query per
        # attendance would have had 1,400 to spare before this noticed. The
        # figure is only a figure because `_ANCHOR` is fixed; against
        # `date.today()` it moved with the weekday composition of the span.
        self.assertEqual(len(self.attendances), 6300)
        budget = (
            _REGENERATION_QUERIES_WITH_WORK_ENTRIES
            if self.env["ir.module.module"].search_count(
                [
                    ("name", "=", "hr_work_entry_attendance"),
                    ("state", "=", "installed"),
                ]
            )
            else _REGENERATION_QUERIES
        )
        t0 = time.time()
        with self.assertQueryCount(budget):
            self.ruleset.action_regenerate_overtimes()
        t1 = time.time()
        _logger.info(
            "Regenerated overtime for %s hr.attendance records in %s seconds.",
            len(self.attendances.ids),
            t1 - t0,
        )


@tagged("post_install", "-at_install")
class TestAttendanceComputeBatchCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employees = cls.env["hr.employee"].create(
            [{"name": f"batch cost {i}"} for i in range(20)]
        )
        now = fields.Datetime.now()
        cls.env["hr.attendance"].create(
            [
                {
                    "employee_id": employee.id,
                    "check_in": now - relativedelta(hours=3),
                    "check_out": now - relativedelta(hours=1),
                }
                for employee in cls.employees
            ]
        )
        cls.env.flush_all()

    def _queries_for(self, compute_name, field_name, count):
        records = self.employees[:count]
        self.env.invalidate_all()
        records.mapped("attendance_ids")
        before = self.env.cr.sql_statement_count
        if field_name is None:
            getattr(records, compute_name)()
        else:
            records.mapped(field_name)
        return self.env.cr.sql_statement_count - before

    def _assert_flat(self, compute_name, field_name=None):
        small = self._queries_for(compute_name, field_name, 2)
        large = self._queries_for(compute_name, field_name, 20)
        self.assertLessEqual(
            large,
            small,
            f"{compute_name} costs {large} queries for 20 employees against "
            f"{small} for 2: it is querying per employee. Two sizes rather than "
            f"one because a single size cannot tell a flat cost from a linear one, "
            f"and 2 rather than 1 so a warm cache cannot make it vacuous.",
        )

    def test_hours_today_does_not_query_per_employee(self):
        self._assert_flat("_compute_hours_today", field_name="hours_today")

    def test_last_attendance_id_does_not_query_per_employee(self):
        self._assert_flat("_compute_last_attendance_id")


@tagged("post_install", "-at_install")
class TestAttendanceComputeQueryScope(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employees = cls.env["hr.employee"].create(
            [{"name": f"scope {i}", "tz": "Europe/Brussels"} for i in range(3)]
        )
        now = fields.Datetime.now()
        cls.env["hr.attendance"].create(
            [
                {
                    "employee_id": employee.id,
                    "check_in": now - relativedelta(hours=3),
                    "check_out": now - relativedelta(hours=1),
                }
                for employee in cls.employees
            ]
        )
        cls.env.flush_all()

    def _sql_for(self, field_name, table):
        self.env.invalidate_all()
        captured = []
        run = self.env.cr.execute

        def spy(query, params=None, *args, **kwargs):
            captured.append(" ".join(str(query).split()))
            return run(query, params, *args, **kwargs)

        self.env.cr.execute = spy
        try:
            self.employees.mapped(field_name)
        finally:
            self.env.cr.execute = run
        return [query for query in captured if table in query]

    def test_hours_this_month_bounds_the_month_in_sql(self):
        selects = self._sql_for("hours_this_month", "hr_attendance")
        self.assertTrue(selects, "reading the field must query hr_attendance")
        self.assertTrue(
            all("check_in" in query for query in selects),
            "the month window must be a database filter: narrowing in Python "
            "makes the cost of a one-month figure grow with the whole history "
            f"behind it. Queries issued: {selects}",
        )

    def test_total_overtime_asks_only_about_the_employees_being_read(self):
        aggregates = self._sql_for("total_overtime", "hr_attendance_overtime_line")
        self.assertTrue(aggregates, "reading the field must query the overtime lines")
        conditions = [
            query.partition(" WHERE ")[2].partition(" GROUP BY ")[0]
            for query in aggregates
        ]
        self.assertTrue(
            all("employee_id" in condition for condition in conditions),
            "the aggregate must be scoped to `self`: unscoped it sums every "
            f"approved line in the database. WHERE clauses seen: {conditions}",
        )

    def test_hours_this_month_ignores_attendances_outside_the_month(self):
        employee = self.employees[0]
        last_year = fields.Datetime.now() - relativedelta(years=1)
        stale = self.env["hr.attendance"].create(
            {
                "employee_id": employee.id,
                "check_in": last_year,
                "check_out": last_year + relativedelta(hours=8),
            }
        )
        this_month = employee.attendance_ids - stale
        self.env.invalidate_all()
        self.assertTrue(
            stale.worked_hours,
            "the excluded attendance must carry hours, or excluding it proves nothing",
        )
        self.assertEqual(
            employee.hours_this_month,
            round(sum(this_month.mapped("worked_hours")), 2),
            "only what was worked this month counts towards it",
        )
