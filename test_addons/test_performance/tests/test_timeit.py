import logging
import timeit
from typing import Literal

from odoo import Command
from odoo.models import BaseModel
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class TestPerformanceTimeit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_performance.simple.minded'].with_context(active_test=False)

        def create_parent(size):
            return cls.Model.create({
                'name': f'parent_{size}_children',
                'child_ids': [
                    Command.create({
                        'name': f'{size}_child_{i}',
                        'active': (i % 4) != 0,
                    })
                    for i in range(size)
                ],
            })
        cls.parent_0_child = create_parent(0)
        cls.parent_1_child = create_parent(1)
        cls.parent_10_children = create_parent(10)
        cls.parent_100_children = create_parent(100)
        cls.parent_1000_children = create_parent(1_000)
        cls.parent_10000_children = create_parent(10_000)

        cls.example_domains = [
            [('id', '<', 100)],
            [('id', '<', 100), ('name', '=like', 'par')],
            [('active', '=', False)],
            [('parent_id.name', 'like', "100")],
            [('parent_id', 'like', "100")],
        ]

    @classmethod
    def get_parents(cls):
        return [
            cls.parent_1_child,
            cls.parent_10_children,
            cls.parent_100_children,
            cls.parent_1000_children,
            cls.parent_10000_children,
        ]

    @classmethod
    def get_test_children(cls, *, max_size=10**6):
        """Get records for testing, give the max size of the recordset"""
        all_records = [p.child_ids for p in cls.get_parents()]
        result = [recs for recs in all_records if len(recs) < max_size]
        # find the next bigger and trucate it to max size
        if bigger := next((recs for recs in all_records if len(recs) > max_size), None):
            result.append(bigger[:max_size])
        return result

    def setUp(self):
        super().setUp()
        # Warm up the cache of all data
        self.Model.with_context(active_test=False).search([]).mapped('name')

    def launch_perf(
        self, code: str, records: BaseModel, *,
        relative_size: int = 1,  # relative size of the batch (for comparisons)
        number: int = 100,  # number of runs in each iteration
        repeat: int = 3,  # number of repeated runs
        ctx: dict = {},  # additional local variables
    ) -> float:
        """Run a performance test.

        Returns the best execution run time in microseconds.
        The number of runs is `number * repeat`.
        """
        assert repeat > 1, "repeat at least twice as the first result is often slower"
        assert number > 0, "number of runs must be positive"
        times = timeit.repeat(code, globals={**ctx, 'records': records}, repeat=repeat, number=number)
        best_mean = min(times) / number * 1_000_000
        if relative_size != 1:
            _logger.info("  `%s` takes %.3fµs (%.3fµs/%d)", code, best_mean / relative_size, best_mean, relative_size)
        else:
            _logger.info("  `%s` takes %.3fµs", code, best_mean)
        return best_mean

    def launch_perf_set(
        self,
        code: str, *,
        record_list: list[BaseModel] | None = None,
        relative_size: list[int] | None = None,
        check_type: Literal['linear', 'maybe-linear', None] = 'linear',
        number: int = 4,
        repeat: int = 3,
        **kw,
    ):
        # initialize the record list with the children records
        if not record_list:
            record_list = self.get_test_children()
        # relative sizes are initialized to 1, 10, 100, ...
        relative_sizes = relative_size or [10 ** i for i in range(len(record_list))]
        assert len(relative_sizes) == len(record_list)
        results = [
            self.launch_perf(code, records=records, relative_size=relative_size, repeat=repeat, number=number, **kw)
            for records, relative_size in zip(record_list, relative_sizes)
        ]
        # checks
        if len(results) <= 3:
            check_type = None
        if check_type in ('linear', 'maybe-linear'):
            # approximative check that the resulting runs are behaving linearly
            # skip the first result as it is very small and not comparable
            check_results = [r / s for r, s in zip(results, relative_sizes)][1:]
            min_time = check_results[0]  # take the time for the first check result as a comparison point
            max_time = max(check_results)
            # just check that the biggest difference of timings per record
            # compared to minimum run time is not greater than the max_tolerance
            max_tolerance = 2.5
            if check_type == 'linear':
                self.assertLess(max_time / min_time, max_tolerance, f"Non-linear behaviour detected, relative results: {check_results}")
            else:
                _logger.info("Linear behaviour result is %s for %s", max_time / min_time < max_tolerance, check_results)
        else:
            self.assertFalse(check_type, "Unsupported check_type")
        return results

    def test_perf_field_get(self):
        self.launch_perf("records.name", self.parent_0_child)

    def test_perf_field_getitem(self):
        self.launch_perf("records['name']", self.parent_0_child)

    def test_perf_field_set(self):
        self.launch_perf("records.name = 'ok'", self.parent_0_child)
        self.launch_perf_set("records.name = records[0].name")

    def test_perf_field_set_flush(self):
        self.launch_perf("records.flush_recordset()", self.parent_0_child)
        self.launch_perf("records.write({'name': 'ok'}); records.flush_recordset()", self.parent_0_child)

    def test_perf_filtered_by_field(self):
        self.launch_perf_set("records.filtered('active')")

    def test_perf_mapped(self):
        self.launch_perf_set("records.mapped('name')")

    def test_perf_sorted(self):
        self.launch_perf_set("records.sorted('name')")

    def test_perf_access_one2many_active_test(self):
        record_list = [
            p.with_context(active_test=True)
            for p in self.get_parents()
        ]
        self.launch_perf_set("records.child_ids", record_list=record_list)

    def test_perf_access_iter(self):
        self.launch_perf_set("list(records)")

    def test_perf_as_query(self):
        self.launch_perf_set("records._as_query()", number=100)

    def test_perf_exists(self):
        self.launch_perf_set("records.exists()")

    def test_perf_search_query(self):
        self.launch_perf("records._search([])", self.Model)
        self.launch_perf("records._search([], limit=10)", self.Model)
        self.launch_perf("records._search([], order='id')", self.Model)
        self.launch_perf("records._search([], order='name')", self.Model)
        self.launch_perf("records._search([], order='parent_id, id desc')", self.Model)

    def test_perf_domain_search(self):
        for domain in self.example_domains:
            self.launch_perf(f"records._search({domain!r})", self.Model)

    def test_perf_domain_filtered(self):
        for domain in self.example_domains:
            self.launch_perf_set(f"records.filtered_domain({domain!r})", repeat=2)

    def test_perf_xxlarge_domain(self):

        def large_domain(records):
            N = len(records)
            return ['|'] * (N - 1) + [('name', '=', 'admin')] * N

        ctx = {'dom': large_domain}
        # _search()
        self.launch_perf_set("records._search(dom(records))",
            ctx=ctx, repeat=2, number=3, check_type='maybe-linear')
        # search() with result, minimal run times, just to check if we can handle the query execution
        self.launch_perf_set("records.search(dom(records))",
            # max is set to 9.5k because for 10k we get an out of memory error
            record_list=self.get_test_children(max_size=9500),
            ctx=ctx, repeat=2, number=1, check_type='maybe-linear')
        # filtered_domain() is non-linear and may time-out!
        self.launch_perf_set("records.filtered_domain(dom(records))",
            record_list=self.get_test_children(max_size=400),
            ctx=ctx, repeat=2, number=2, check_type=None)

    def test_perf_xxlarge_domain_unique(self):

        def large_domain_uniq(records):
            N = len(records)
            return ['|'] * (N - 1) + [('name', '=', str(i)) for i in range(N)]

        ctx = {'dom': large_domain_uniq}
        self.launch_perf_set("records._search(dom(records))",
            ctx=ctx, repeat=2, number=3, check_type='maybe-linear')
