"""Benchmark methods and transaction isolation for repeated rounds."""

import logging
import re
import sys
from contextlib import closing, contextmanager
from enum import StrEnum
from functools import wraps
from unittest.mock import patch
from urllib.parse import quote

from odoo import sql_db
from odoo.tests import common
from odoo.tests.case import _Outcome
from odoo.tests.common import (
    TransactionCase,
    _preserve_cursor_callbacks,
    no_retry,
    tagged,
)
from odoo.tools import config

from .collectors import collect
from .reporting import Result, format_results_table

logger = logging.getLogger('odoo.benchmark')
NAME_RE = re.compile(r'[A-Za-z0-9_.-]+', re.ASCII)


def validate_name(name):
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        raise ValueError(f"Invalid benchmark name {name!r}: expected [A-Za-z0-9_.-]+")


def benchmark(func=None, *, name=None, warmups=None, rounds=None):
    """Mark a benchmark method, with optional name and round counts.

    Methods need no naming prefix. Without measure() blocks the whole body and
    its final flush are measured; otherwise only the blocks are measured.
    name adds a reporting label matching [A-Za-z0-9_.-]+; selectors still use
    the actual method name.
    Warmup and measured round counts use CLI > decorator > class settings,
    defaulting to 1 warmup and 3 measured rounds.
    Use @users outside this decorator. Do not combine it with @warmup.
    """
    if name is not None:
        validate_name(name)

    def decorate(method):
        if hasattr(method, '_users'):
            msg = '@users must be outside @benchmark'
            raise ValueError(msg)
        if hasattr(method, '_warmup'):
            msg = '@warmup cannot be combined with @benchmark'
            raise ValueError(msg)

        @wraps(method)
        def run(self, *args, **kwargs):
            return self._run_benchmark(method, settings, args, kwargs)

        settings = {'name': name, 'warmups': warmups, 'rounds': rounds}
        run._benchmark = settings
        return run

    return decorate(func) if func is not None else decorate


class RoundMode(StrEnum):
    WARMUP = 'warmup'
    MEASURE = 'measure'
    PROFILE = 'profile'


class Round:
    """One benchmark execution in warmup, measurement or profiling mode.

    Measure the whole method or individual blocks. Blocks share one transaction
    and report separate results. Warmups and profiling add no measured samples.
    """

    def __init__(self, case, *, mode: RoundMode | str, profile_frame=None):
        self.case = case
        self.mode = RoundMode(mode)
        self.profile_frame = profile_frame
        # [] means whole-method measurement; [None] means one unnamed block.
        # They share a result key but require different profiling scopes.
        self.regions: list[str | None] = []
        self.values = {}
        self.active = None
        self.in_block = False

    @contextmanager
    def measurement(self, key):
        """Apply warmup, metric or profile instrumentation to either measurement scope."""
        if self.mode is RoundMode.PROFILE:
            with self.case.profile(description=key, init_frame=self.profile_frame) as profiler:
                yield {}
            profile_id = getattr(profiler, 'profile_id', None)
            if not profile_id:
                raise RuntimeError(f'Could not save benchmark profile for {key}')
            # The profiler can catch a storage/commit OperationalError after
            # assigning profile_id. Verify on a fresh transaction: the test
            # transaction's repeatable-read snapshot cannot see new profiles.
            with sql_db.db_connect(self.case.cr.dbname).cursor() as cr:
                cr.execute('SELECT id FROM ir_profile WHERE id = %s', [profile_id])
                if not cr.fetchone():
                    raise RuntimeError(f'Could not save benchmark profile for {key}')
        elif self.mode is RoundMode.MEASURE:
            with collect() as metrics:
                yield metrics
        else:
            yield {}

    def start(self, name=None):
        key = self.case._region_key(name)
        self.active = self.measurement(key)
        # Whole-method measurement starts before we know whether the method
        # uses blocks. The first block must be able to close and discard it.
        return self.active.__enter__()  # noqa: PLC2801 - the first block stops provisional measurement

    def stop(self, exc_info=(None, None, None)):
        # sys.exc_info() can contain an enclosing handled exception even when
        # this scope succeeded. Only the caller knows whether its scope failed.
        active, self.active = self.active, None
        if active is not None:
            active.__exit__(*exc_info)

    @contextmanager
    def measure(self, name):
        if self.in_block:
            msg = 'Measured blocks cannot be nested'
            raise ValueError(msg)
        if name is not None:
            validate_name(name)
        if name in self.regions:
            raise ValueError(f'Duplicate measurement name {name!r}')
        if self.regions and (name is None or None in self.regions):
            msg = 'Multiple measured blocks must all have names'
            raise ValueError(msg)
        if not self.regions:
            self.stop()
            self.values.clear()
        self.regions.append(name)
        self.case.cr.flush()
        self.in_block = True
        try:
            metrics = self.start(name)
            try:
                yield
                self.case.cr.flush()
            except BaseException:
                self.stop(sys.exc_info())
                raise
            else:
                self.stop()
        finally:
            self.in_block = False
        self.values[name] = metrics


@no_retry
@tagged('benchmark', '-standard', '-at_install', 'post_install')
class BenchmarkCase(TransactionCase):
    """Benchmark business flows on existing data or setUpClass fixtures.

    Only methods decorated with @benchmark are discovered. Run them with
    ``odoo-bin benchmark -d db -t /my_addon``. For example::

        class OrderFlows(BenchmarkCase):
            @benchmark(rounds=5)
            def confirm(self):
                orders = self.env['sale.order'].search([('state', '=', 'draft')])
                with self.measure():
                    orders.action_confirm()

    Without measure() blocks the whole method is measured. A block excludes
    preparation before it, flushes pending work before measurement, and includes
    its final flush. Use distinct names for multiple sequential blocks; their
    names and order must stay the same in every round. Blocks cannot nest.

    warmups and rounds class attributes default to 1 and 3. @benchmark settings
    override them, and --warmups/--rounds override both. Warmups are discarded.
    --profile saves one additional execution without including it in the results.

    Every round repeats the method, including preparation; class and test setup
    run once. Record caches start cold, but preparation can warm them before a
    measured block. ORM method caches can remain warm across rounds. Database
    changes are rolled back; Python state and independently committed work are
    not restored.

    Commits and HTTP flows are not supported.
    Use @users outside @benchmark for one result per user;
    recordsets created in setUpClass must be rebound to self.env when switching users.
    Execution errors fail a benchmark; missing data can raise unittest.SkipTest.
    """
    warmups = 1
    rounds = 3

    def __init__(self, methodName='runTest'):  # noqa: N803 - keep unittest.TestCase's keyword argument
        super().__init__(methodName)
        self._benchmark_round: Round | None = None
        # Map each published result key to its Python module, class and method.
        # Different files can produce the same reporting key; reject duplicates
        # rather than emit indistinguishable statistics. The CLI shares this
        # mapping across cases so collisions are detected across the whole run.
        self._benchmark_keys = {}

    @classmethod
    def setUpClass(cls):
        cls._benchmark_results = []
        super().setUpClass()
        # BaseCase installs this conditionally on 'standard', which we remove.
        # Passing the bound method directly would discard requests' session.
        cls.startClassPatcher(patch.object(
            common.requests.sessions.Session, 'send',
            lambda session, request, **kwargs: cls._request_handler(session, request, **kwargs),  # noqa: PLW0108
        ))

    @classmethod
    def tearDownClass(cls):
        try:
            if cls._benchmark_results:
                logger.info('%s\n%s', cls.__name__, format_results_table(cls._benchmark_results))
        finally:
            super().tearDownClass()

    def _run_benchmark(self, method, settings, args, kwargs):
        """Resolve settings, execute all rounds, then publish results per region.

        Each round must measure the same regions in the same order. Retain only
        measured samples; warmups and the optional final profile add no samples.
        Keep samples local until every round succeeds, including subtests and
        profiling, so a failed invocation cannot publish partial statistics.
        """
        if self._benchmark_round is not None:
            msg = 'Benchmark methods cannot be nested'
            raise ValueError(msg)
        # Resolve CLI > decorator > class settings before doing any round work.
        counts = {}
        for setting, default in (('warmups', 1), ('rounds', 3)):
            value = config.get(f'benchmark_{setting}')
            if value is None:
                value = settings[setting]
            if value is None:
                value = getattr(self, setting, default)
            if not isinstance(value, int) or isinstance(value, bool) or value < (0 if setting == 'warmups' else 1):
                raise ValueError(f'Invalid benchmark {setting}: {value!r}')
            counts[setting] = value

        key = self._make_canonical_tag(
            tag='benchmark', module=self.test_module,
            test_class=type(self).__name__, test_method=self._testMethodName,
        )
        if settings['name'] is not None:
            key += '#' + settings['name']
        self._benchmark_key = key
        self._benchmark_login = '' if self.env.su else '@' + quote(self.env.user.login, safe='_.-~')
        reference_regions = None
        samples = {}
        modes = [RoundMode.WARMUP] * counts['warmups'] + [RoundMode.MEASURE] * counts['rounds']
        if config.get('benchmark_profile'):
            modes.append(RoundMode.PROFILE)

        # subTest() records failures without raising. Each invocation needs its
        # own success flag, including repeated failures that results deduplicate.
        previous_warm = self.warm
        previous_outcome = self._outcome
        execution = _Outcome(self, previous_outcome.result) if previous_outcome else None
        self._outcome = execution
        try:
            for mode in modes:
                # 'warm' enables query assertions; warmup executions skip them.
                self.warm = mode is not RoundMode.WARMUP

                regions, values = self._round(method, args, kwargs, mode=mode, profile_blocks=bool(reference_regions))

                if execution and not execution.success:
                    return
                if reference_regions is None:
                    reference_regions = regions
                elif regions != reference_regions:
                    # Mixing different scopes would produce misleading medians.
                    raise ValueError(f'Measurement regions changed for {key}: {reference_regions!r} -> {regions!r}')
                if mode is RoundMode.MEASURE:
                    for name, metrics in values.items():
                        samples.setdefault(name, []).append(metrics)
        finally:
            self.warm = previous_warm
            self._outcome = previous_outcome
            if execution:
                previous_outcome.success &= execution.success

        # Validate every result and key before publishing or reserving any key.
        results = [Result(self._region_key(name), values) for name, values in samples.items()]
        keys = self._benchmark_keys
        source = f'{type(self).__module__}.{type(self).__qualname__}.{self._testMethodName}'
        for item in results:
            if item.key in keys:
                raise ValueError(f'Duplicate benchmark key {item.key}: {keys[item.key]} and {source}')
        for item in results:
            keys[item.key] = source
            item.publish()
        type(self)._benchmark_results.extend(results)

    def _region_key(self, name):
        return self._benchmark_key + (f'#{name}' if name is not None else '') + self._benchmark_login

    def _round(self, method, args, kwargs, *, mode: RoundMode | str, profile_blocks=False):
        """Execute one isolated round; return ordered region names and their metrics.

        On success or failure, stop collectors, roll back and release the
        savepoint, clear pending ORM state, then restore cursor callbacks.
        """
        mode = RoundMode(mode)
        try:
            self.cr.flush()
            self.env.invalidate_all(flush=False)
        except BaseException:
            self.env.transaction.clear()
            raise
        # A generator wrapper's entry frame is suspended while its body runs.
        # This method remains on the stack and provides the profiler boundary.
        state = self._benchmark_round = Round(self, mode=mode, profile_frame=sys._getframe() if mode is RoundMode.PROFILE else None)
        try:
            with _preserve_cursor_callbacks(self.cr):
                try:
                    # closing forces rollback even after successful execution.
                    with closing(self.cr.savepoint(flush=False)):
                        try:
                            # The metric rounds already established profile scope.
                            # Block-based profiling needs no provisional profile.
                            if not (mode is RoundMode.PROFILE and profile_blocks):
                                state.values[None] = state.start()

                            method(self, *args, **kwargs)

                            self.cr.flush()
                        except BaseException:
                            state.stop(sys.exc_info())
                            raise
                        else:
                            state.stop()
                            return tuple(state.regions), state.values
                finally:
                    # Never flush pending ORM work after rolling back its data.
                    self.env.transaction.clear()
        finally:
            self._benchmark_round = None
            state.profile_frame = None

    def measure(self, name=None):
        """Measure a block inside @benchmark, excluding preparation before it.

        Entry flushes pending writes/precommit work before collecting; exit
        flushes while collecting. No entry invalidation: new() and preparation's
        cached records remain usable. Blocks are sequential, never nested. A
        sole unnamed block preserves the method key; multiple blocks require
        unique ASCII names and the same order in every round, including profiles.
        """
        state = self._benchmark_round
        if state is None:
            msg = 'measure() requires an active @benchmark method'
            raise ValueError(msg)
        return state.measure(name)
