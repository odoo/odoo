"""Scenarios executed by test_benchmark.py's CLI subprocess tests."""

from unittest import SkipTest

from odoo.tests import BenchmarkCase, benchmark, tagged


class Probe(BenchmarkCase):
    @benchmark
    def ping(self):
        self.cr.execute('SELECT 1')

    @benchmark
    def blocks(self):
        with self.measure('first'):
            self.cr.execute('SELECT 1')
        with self.measure('second'):
            self.cr.execute('SELECT 2')

    def helper(self):
        msg = 'Undecorated helper must not run'
        raise AssertionError(msg)


@tagged('-benchmark', 'benchmark_cli_skip')
class Skipped(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        msg = 'Missing benchmark fixture'
        raise SkipTest(msg)

    @benchmark
    def ping(self):
        msg = 'Skipped fixture must not run'
        raise AssertionError(msg)


@tagged('-benchmark', 'benchmark_cli_error')
class Broken(BenchmarkCase):
    @benchmark
    def ping(self):
        msg = 'Benchmark fixture failure'
        raise ValueError(msg)


@tagged('-benchmark', 'benchmark_cli_setup_error')
class BrokenSetup(BenchmarkCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        msg = 'Benchmark fixture setup failure'
        raise ValueError(msg)

    @benchmark
    def ping(self):
        pass
