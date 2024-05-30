import logging
import timeit

from odoo.tests.common import TransactionCase
from odoo import Command

_logger = logging.getLogger(__name__)


class TestPerformanceTimeit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Model = cls.env['test_performance.simple.minded'].with_context(active_test=False)
        cls.parent_0_child = cls.Model.create({
            'name': 'parent_0_child',
        })
        cls.parent_10_children = cls.Model.create({
            'name': 'parent_10_children',
            'child_ids': [
                Command.create({
                    'name': f'10_child_{i}',
                    'active': (i % 4) != 0,
                })
                for i in range(10)
            ],
        })
        cls.parent_1000_children = cls.Model.create({
            'name': 'parent_1000_children',
            'child_ids': [
                Command.create({
                    'name': f'1000_child_{i}',
                    'active': (i % 4) != 0,
                })
                for i in range(1000)
            ],
        })
        cls.parent_10000_children = cls.Model.create({
            'name': 'parent_10000_children',
            'child_ids': [
                Command.create({
                    'name': f'10000_child_{i}',
                    'active': (i % 4) != 0,
                })
                for i in range(10000)
            ],
        })

    def setUp(self):
        super().setUp()
        # Warm up the cache of all data
        self.Model.with_context(active_test=False).search([]).mapped('name')

    def launch_perf(self, code, records, number):
        times = timeit.repeat(code, globals={'records': records}, number=number)
        return min(times) / number

    def test_perf_field_get(self):
        best_time = self.launch_perf("records.name", self.parent_0_child, number=10_000)
        _logger.info("__get__ (`record.name`) takes %.3f µs", best_time * 1_000_000)

    def test_perf_model_getitem(self):
        best_time = self.launch_perf("records['name']", self.parent_0_child, number=10_000)
        _logger.info("__getitem__ (`record['name']`) takes %.3f µs", best_time * 1_000_000)

    def test_perf_filtered(self):
        for records in (
            self.parent_0_child,
            self.parent_10_children.child_ids,
            self.parent_1000_children.child_ids,
            self.parent_10000_children.child_ids,
        ):
            best_time = self.launch_perf("records.filtered('active')", records, number=10)
            _logger.info(
                "BaseModel.filtered() (`records.filtered('active')`) takes %.3f µs (%s records)",
                best_time * 1_000_000,
                len(records),
            )

    def test_perf_mapped(self):
        for records in (
            self.parent_0_child,
            self.parent_10_children.child_ids,
            self.parent_1000_children.child_ids,
            self.parent_10000_children.child_ids,
        ):
            best_time = self.launch_perf("records.mapped('name')", records, number=10)
            _logger.info(
                "BaseModel.mapped() (`records.mapped('name')`) takes %.3f µs (%s records)",
                best_time * 1_000_000,
                len(records),
            )

    def test_perf_sorted(self):
        for records in (
            self.parent_0_child,
            self.parent_10_children.child_ids,
            self.parent_1000_children.child_ids,
            self.parent_10000_children.child_ids,
        ):
            best_time = self.launch_perf("records.sorted('name')", records, number=10)
            _logger.info(
                "BaseModel.sorted() (`records.sorted('name')`) takes %.3f µs (%s records)",
                best_time * 1_000_000,
                len(records),
            )

    def test_perf_access_one2many(self):
        for records in (
            self.parent_0_child,
            self.parent_10_children,
            self.parent_1000_children,
            self.parent_10000_children,
        ):
            best_time = self.launch_perf("records.child_ids", records.with_context(active_test=True), number=10)
            _logger.info(
                "Access One2many (`record.child_ids`) takes %.3f µs (%s children) with active_test=True",
                best_time * 1_000_000,
                len(records.child_ids),
            )

    def test_perf_access_iter(self):
        for records in (
            self.parent_0_child,
            self.parent_10_children.child_ids,
            self.parent_1000_children.child_ids,
            self.parent_10000_children.child_ids,
        ):
            best_time = self.launch_perf("list(records)", records, number=10)
            _logger.info(
                "__iter__ (`list(records)`) takes %.3f µs (%s records)",
                best_time * 1_000_000,
                len(records),
            )
