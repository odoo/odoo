"""Benchmark test methods with repeatable database state."""

import logging
import os
import re
from contextlib import ExitStack, closing, contextmanager, nullcontext
from unittest.mock import patch
from urllib.parse import quote

import requests

from odoo.tests.case import _Outcome
from odoo.tests.common import (
    TransactionCase,
    _preserve_cursor_callbacks,
    no_retry,
    tagged,
)
from odoo.tools import str2bool

from .collectors import Collector, collect
from .reporting import Result, format_results_table

_logger = logging.getLogger('odoo.benchmark')
NAME_RE = re.compile(r'[A-Za-z0-9_.-]+', re.ASCII)
ODOO_BENCHMARK_SHOW_TABLE = str2bool(os.getenv('ODOO_BENCHMARK_SHOW_TABLE', '1'))


class Round:
    """Run one benchmark execution and roll back its database changes on exit."""

    def __init__(self, case, *, measured):
        self.case = case  # Test case providing the cursor, environment and collectors.
        self.measured = measured  # False for warmups, which produce no metric samples.
        self.scopes = []  # Block paths in entry order, used to compare executions.
        self.measurements = {}  # Name -> metrics; None means the whole method or one unnamed block.
        self._scope_stack = []  # Currently open scope names, with the innermost last.
        self._whole_method = ExitStack()  # Provisional collection, discarded when blocks appear.
        self._cleanup = ExitStack()  # Restore the savepoint, ORM state and callbacks.

    def __enter__(self):
        try:
            self.case.cr.flush()
            self.case.env.invalidate_all(flush=False)
        except BaseException:
            self.case.env.transaction.clear()
            raise
        try:
            self._cleanup.enter_context(_preserve_cursor_callbacks(self.case.cr))
            # Stop collectors before rollback, then clear ORM state and restore callbacks.
            self._cleanup.callback(self.case.env.transaction.clear)
            self._cleanup.enter_context(closing(self.case.cr.savepoint(flush=False)))
            self.case._benchmark_current_round = self
            self._cleanup.callback(setattr, self.case, '_benchmark_current_round', None)
            self._cleanup.callback(self._whole_method.close)
            self.measurements[None] = self._whole_method.enter_context(self._collect())
        except BaseException:
            self._cleanup.close()
            raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.case.cr.flush()
        finally:
            self._cleanup.close()

    def _collect(self):
        return collect(self.case._benchmark_collectors, self.case) if self.measured else nullcontext({})

    @contextmanager
    def measure(self, name):
        if name is not None and (not isinstance(name, str) or not NAME_RE.fullmatch(name)):
            raise ValueError(f"Invalid benchmark name {name!r}: expected [A-Za-z0-9_.-]+")

        if self.scopes and name in self.measurements:
            raise ValueError(f'Duplicate measurement name {name!r}')

        if self.scopes and (name is None or None in self.measurements):
            msg = 'Multiple measured blocks must all have names'
            raise ValueError(msg)

        if not self.scopes:
            self._whole_method.close()
            self.measurements.clear()

        self.case.cr.flush()  # Exclude pending preparation from this scope.

        with self._collect() as metrics:
            # Insert on entry so parents appear before children in the report.
            self.measurements[name] = metrics
            self._scope_stack.append(name)
            self.scopes.append(tuple(self._scope_stack))
            try:
                yield
                self.case.cr.flush()
            finally:
                self._scope_stack.pop()


@no_retry
@tagged('benchmark', '-standard', '-at_install', 'post_install')
class BenchmarkCase(TransactionCase):
    """Write performance benchmarks as ordinary Odoo tests.

    Create tests/test_benchmark.py (arbitrary filename) in your addon and add
    ``from . import test_benchmark`` to tests/__init__.py. Inherit BenchmarkCase
    and write test_ methods:

    .. code-block:: python

        from odoo.tests import BenchmarkCase

        class BenchmarkPartnerWrite(BenchmarkCase):
            warmups = 1
            rounds = 3
            collectors = ('wall', 'cpu', 'sql')

            @classmethod
            def setUpClass(cls):
                super().setUpClass()
                cls.partners = cls.env['res.partner'].create([
                    {'name': f'Partner {i}'} for i in range(100)
                ])

            def test_rename(self):
                self.partners.write({'name': 'Renamed'})

    Run against a database where the addon is installed:

    .. code-block:: bash

        odoo-bin -d bench_db --test-tags=benchmark/my_addon --stop-after-init

    Benchmarks are excluded from standard test runs. Each method runs once to
    warm caches, then three times to collect results by default. Override these
    counts on the class. Results include summary statistics and a Markdown table.

    setUpClass() and setUp() run once. Each execution starts from their database
    state, and its changes are rolled back, like normal tests.
    Record caches are cleared between executions; Python attributes,
    HTTP sessions and ORM method caches persist.
    Do not add @warmup: warmups are already handled by this class.

    The whole method is measured, including its final flush. To exclude
    preparation, put the operation inside a measurement block:

    .. code-block:: python

        def test_rename_and_archive(self):
            partners = self.partners.filtered('active')
            with self.measure('rename'):
                partners.write({'name': 'Renamed'})
            with self.measure('archive'):
                partners.write({'active': False})

    Blocks may nest to report a complete flow and its individual phases:

    .. code-block:: python

        with self.measure('rename_and_archive'):
            with self.measure('rename'):
                partners.write({'name': 'Renamed'})
            with self.measure('archive'):
                partners.write({'active': False})

    Parent measurements include all child work, so their results overlap.
    Multiple blocks need unique names, with the same order and nesting in every
    execution. One unnamed block is also allowed when it is the only block.

    Select collectors on the class: 'wall' measures elapsed time, 'cpu' measures
    Odoo process CPU time, and 'sql' measures SQL time and query counts by type.
    @users gives separate results per user; rebind shared recordsets with
    with_env(self.env). Inherit both BenchmarkCase and HttpCase for HTTP helpers;
    use authenticate() to log the HTTP client in.
    """
    warmups = 1
    rounds = 3
    collectors = ('wall', 'cpu', 'sql')

    def __init__(self, methodName='runTest'):  # noqa: N803 - keep unittest.TestCase's keyword argument
        super().__init__(methodName)
        self._benchmark_current_round: Round | None = None

    @classmethod
    def setUpClass(cls):
        cls._benchmark_results = []
        super().setUpClass()
        # BaseCase installs this conditionally on 'standard', which we remove.
        # Passing the bound method directly would discard requests' session.
        cls.startClassPatcher(patch.object(
            requests.sessions.Session, 'send',
            lambda session, request, **kwargs: cls._request_handler(session, request, **kwargs),  # noqa: PLW0108
        ))

    @classmethod
    def tearDownClass(cls):
        if cls._benchmark_results and ODOO_BENCHMARK_SHOW_TABLE:
            _logger.info('%s', format_results_table(cls._benchmark_results))
        super().tearDownClass()

    def _callTestMethod(self, method):
        self._check_settings(method)
        if hasattr(method, '_users'):
            super()._callTestMethod(method)
        else:
            self._run_benchmark(method)

    def _callTestMethodForUser(self, method, *args, **kwargs):
        test_method = getattr(self, self._testMethodName, None)
        # Repeat only the selected test; @users helpers execute normally,
        # including during setup and inside an active round.
        if self._benchmark_current_round is not None or method is not getattr(test_method, '_users_method', None):
            super()._callTestMethodForUser(method, *args, **kwargs)
        else:
            self._run_benchmark(method, self, *args, **kwargs)

    def _check_settings(self, method):
        if hasattr(method, '_warmup'):
            msg = '@warmup cannot be combined with BenchmarkCase'
            raise ValueError(msg)

        for setting, minimum in (('warmups', 0), ('rounds', 1)):
            value = getattr(self, setting)
            if type(value) is not int or value < minimum:
                raise ValueError(f'Invalid benchmark {setting}: {value!r}')

        if not self.collectors:
            msg = 'At least one benchmark collector is required'
            raise ValueError(msg)

        self._benchmark_collectors = tuple(Collector[name] for name in self.collectors)
        keys = [metric.key for collector in self._benchmark_collectors for metric in collector.metrics]
        if len(keys) != len(set(keys)):
            msg = 'Benchmark collectors must declare distinct metric keys'
            raise ValueError(msg)

    def _run_benchmark(self, method, *args, **kwargs):
        key = 'benchmark' + self.canonical_tag
        login = '' if self.env.su else '@' + quote(self.env.user.login, safe='_.-~')
        reference_scopes = None
        samples_by_block = {}

        # subTest() records failures without raising. Each invocation needs its
        # own success flag, including repeated failures that results deduplicate.
        previous_warm = self.warm
        previous_outcome = self._outcome
        execution = _Outcome(self, previous_outcome.result) if previous_outcome else None
        self._outcome = execution
        try:
            for index in range(self.warmups + self.rounds):
                # 'warm' enables query assertions; warmup executions skip them.
                self.warm = index >= self.warmups

                with Round(self, measured=self.warm) as benchmark_round:
                    method(*args, **kwargs)

                if execution and not execution.success:
                    return
                # Every execution must measure the same blocks, in the same order and nesting.
                scopes = tuple(benchmark_round.scopes)
                if reference_scopes is None:
                    reference_scopes = scopes
                elif scopes != reference_scopes:
                    raise ValueError(f'Measurement scopes changed for {key}: {reference_scopes!r} -> {scopes!r}')
                if self.warm:
                    for name, metrics in benchmark_round.measurements.items():
                        samples_by_block.setdefault(name, []).append(metrics)
        finally:
            self.warm = previous_warm
            self._outcome = previous_outcome
            if execution:
                previous_outcome.success &= execution.success

        results = []
        for name, values in samples_by_block.items():
            label = f'{key}#{name}' if name is not None else key
            results.append(Result(label + login, values, self._benchmark_collectors))
        for result in results:
            result.publish()
        self._benchmark_results.extend(results)

    def measure(self, name=None):
        """Measure a block, excluding preparation before it and including its flush.

        Blocks may nest; parents include their children's time and metrics.
        Multiple blocks need unique names and the same order and nesting each round.
        Readings are retained when an enclosing assertion catches an exception.
        """
        current_round = self._benchmark_current_round
        if current_round is None:
            msg = 'measure() requires an active benchmark round'
            raise ValueError(msg)
        return current_round.measure(name)
