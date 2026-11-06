import logging
import sys
import threading
from types import ModuleType, SimpleNamespace
from unittest import SkipTest
from unittest.mock import patch

from odoo import sql_db
from odoo.http import Controller, request, route
from odoo.tests import BenchmarkCase, HttpCase, TransactionCase, tagged, users
from odoo.tests.benchmark.collectors import Collector, Metric, QueryCollector, collect
from odoo.tests.benchmark.reporting import Result, format_results_table
from odoo.tests.common import new_test_user
from odoo.tests.loader import get_module_test_cases, get_test_modules
from odoo.tests.result import OdooTestResult
from odoo.tests.tag_selector import TagsSelector
from odoo.tools import mute_logger


class TestBenchmarkCollectors(TransactionCase):

    def test_registration_requires_explicit_unique_names(self):
        with patch.dict(Collector._registry):
            class ExperimentalSQL(QueryCollector):
                pass

            self.assertIs(Collector['sql'], QueryCollector)
            self.assertNotIn(ExperimentalSQL, Collector._registry.values())

            class NamedSQL(QueryCollector):
                name = 'test_sql'

            self.assertIs(Collector['test_sql'], NamedSQL)
            for name in ('sql', 'test_sql'):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'already registered'):
                    type('ConflictingSQL', (QueryCollector,), {'name': name})
            self.assertIs(Collector['sql'], QueryCollector)
            self.assertIs(Collector['test_sql'], NamedSQL)

            for name in ('', 1):
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'non-empty string'):
                    type('InvalidCollector', (Collector,), {'name': name})

    def test_builtin_collectors_and_query_classification(self):
        with sql_db.db_connect(self.cr.dbname).cursor() as cr:
            with collect((Collector['wall'], Collector['cpu'], Collector['sql'])) as values:
                cr.execute('CREATE TEMP TABLE benchmark_queries (value integer)')
                cr.execute('INSERT INTO benchmark_queries VALUES (1)')
                cr.execute('UPDATE benchmark_queries SET value = 2')
                cr.execute('SELECT value FROM benchmark_queries')
                cr.execute('DELETE FROM benchmark_queries')
                cr.execute('WITH example AS (SELECT 1) SELECT * FROM example')
        self.assertEqual({key: values[key] for key in ('queries', 'select', 'insert', 'update', 'delete', 'other')},
                         {'queries': 6, 'select': 1, 'insert': 1, 'update': 1, 'delete': 1, 'other': 2})
        for key in ('wall_s', 'cpu_s', 'sql_s'):
            self.assertGreater(values[key], 0)

    def test_named_extension_and_default_aggregation(self):
        with patch.dict(Collector._registry):
            class Tokens(Collector):
                name = 'test_tokens'
                metrics = (Metric('tokens', show_range=True),)

                def stop(self):
                    return {'tokens': 10}

            factories = (Collector['test_tokens'],)
            with collect(factories) as values:
                pass
            result = Result('benchmark/example', [values, {'tokens': 20}], factories)

        self.assertEqual(result.metrics, {'tokens': 15})
        table = format_results_table([result])
        self.assertIn('tokens min-max', table)
        self.assertIn('10-20', table)
        self.assertNotIn('wall', table)
        with self.assertLogs('odoo.benchmark.stats', logging.INFO) as logs:
            result.publish()
        self.assertIn('tokens=15', logs.output[0])

    def test_collectors_stop_in_reverse_order_on_failure(self):
        events = []
        with patch.dict(Collector._registry):
            class First(Collector):
                name = 'test_first'
                metrics = (Metric('first'),)

                def start(self):
                    events.append('start first')

                def stop(self):
                    events.append('stop first')
                    return {'first': 1}

            class Second(First):
                name = 'test_second'
                start_order = 1
                metrics = (Metric('second'),)

                def start(self):
                    events.append('start second')

                def stop(self):
                    events.append('stop second')
                    return {'second': 2}

            with self.assertRaisesRegex(ValueError, 'workload'), collect((Collector['test_second'], Collector['test_first'])) as values:
                msg = 'workload'
                raise ValueError(msg)

        self.assertEqual(events, ['start first', 'start second', 'stop second', 'stop first'])
        self.assertEqual(values, {'first': 1, 'second': 2})


class TestBenchmarkRounds(TransactionCase):
    def setUp(self):
        super().setUp()
        self.record = self.env['test_testing_utilities.benchmark'].create({'value': 7})
        self.stats_log = self.enterContext(patch('odoo.tests.benchmark.reporting._logger_stats.info'))
        self.query_hooks = list(getattr(threading.current_thread(), 'query_hooks', ()))
        self.addCleanup(lambda: self.assertEqual(getattr(threading.current_thread(), 'query_hooks', []), self.query_hooks))

    def _make_case(self, cls):
        cls._benchmark_results = []
        case = cls('test_flow')
        case.env, case.cr = self.env, self.cr
        # Borrow this test's fixtures; still exercise run(), outcomes and invocation.
        case.setUp = lambda: None
        return case

    def _run_case(self, cls):
        result = OdooTestResult()
        case = self._make_case(cls)
        case.run(result)
        return case, result

    def test_normal_discovery_and_selection(self):
        self.assertIn(sys.modules[__name__], get_test_modules('test_tests'))
        module = ModuleType(__name__ + '.discovery')

        class Flow(BenchmarkCase):
            def test_flow(self):
                pass

            def helper(self):
                self.fail('helpers must not be discovered')

        Flow.__module__ = module.__name__
        module.Flow = Flow
        cases = list(get_module_test_cases(module))
        self.assertEqual([case._testMethodName for case in cases], ['test_flow'])
        self.assertTrue(TagsSelector('benchmark/test_tests').check(cases[0]))
        self.assertFalse(TagsSelector('standard').check(cases[0]))
        self.assertEqual(Flow.test_tags, {'benchmark', 'post_install'})
        self.assertFalse(Flow._retry)

    def test_round_counts_rollback_and_final_flush(self):
        record = self.record
        calls = []

        class Flow(BenchmarkCase):
            warmups = 1
            rounds = 2
            collectors = ('sql',)

            def test_flow(self):
                calls.append(self.warm)
                self.assertEqual((record.value, record.double), (7, 14))
                record.value = 9

        case, outcome = self._run_case(Flow)
        self.assertTrue(outcome.wasSuccessful())
        self.assertEqual(calls, [False, True, True])
        self.assertEqual((record.value, record.double), (7, 14))
        result, = Flow._benchmark_results
        self.assertEqual(result.rounds, 2)
        self.assertEqual(result.metrics['update'], 1)
        self.assertIsNone(case._benchmark_current_round)
        self.stats_log.assert_called_once()

    def test_blocks_exclude_preparation_include_children_and_restore_callbacks(self):
        record = self.record
        original_callbacks = list(self.cr.postcommit._funcs)
        self.cr.postcommit.data['benchmark'] = {'items': [1]}

        class Flow(BenchmarkCase):
            rounds = 2
            collectors = ('wall', 'sql')

            def test_flow(self):
                self.assertEqual(self.cr.postcommit.data['benchmark'], {'items': [1]})
                self.cr.postcommit.data['benchmark']['items'].append(2)
                self.cr.postcommit.add(lambda: None)
                record.value = 8
                transient = record.new({'value': 3})
                with self.measure('flow'):
                    with self.measure('write'):
                        self.assertEqual(transient.value, 3)
                        record.value = 9
                    with self.measure('read'):
                        self.cr.execute('SELECT 1')
                with self.measure('after'):
                    self.cr.execute('SELECT 2')

        _, outcome = self._run_case(Flow)
        self.assertTrue(outcome.wasSuccessful())
        parent, write, _read, _after = Flow._benchmark_results
        self.assertEqual([result.key.rsplit('#', 1)[1] for result in Flow._benchmark_results],
                         ['flow', 'write', 'read', 'after'])
        self.assertEqual([result.metrics['queries'] for result in Flow._benchmark_results], [2, 1, 1, 1])
        self.assertEqual(write.metrics['update'], 1)
        self.assertGreaterEqual(parent.metrics['wall_s'], write.metrics['wall_s'])
        self.assertEqual(self.cr.postcommit.data['benchmark'], {'items': [1]})
        self.assertEqual(list(self.cr.postcommit._funcs), original_callbacks)
        self.assertEqual(record.value, 7)

    def test_unnamed_block_excludes_preparation(self):
        class Flow(BenchmarkCase):
            warmups = 0
            rounds = 1
            collectors = ('sql',)

            def test_flow(self):
                self.cr.execute('SELECT 0')
                with self.measure():
                    self.cr.execute('SELECT 1')

        _, outcome = self._run_case(Flow)
        self.assertTrue(outcome.wasSuccessful())
        result, = Flow._benchmark_results
        self.assertEqual(result.metrics['queries'], 1)
        self.assertTrue(result.key.endswith('.test_flow'))

    def test_expected_exceptions_preserve_parent_and_child_measurements(self):
        for assertion_first in (False, True):
            class Flow(BenchmarkCase):
                rounds = 2
                collectors = ('sql',)

                def test_flow(self):
                    with self.measure('parent'):
                        if assertion_first:
                            with self.assertRaises(ValueError), self.measure('rejected'):
                                self.cr.execute('SELECT 1')
                                msg = 'expected'
                                raise ValueError(msg)
                        else:
                            with self.measure('rejected'), self.assertRaises(ValueError):
                                self.cr.execute('SELECT 1')
                                msg = 'expected'
                                raise ValueError(msg)

            with self.subTest(assertion_first=assertion_first):
                _, outcome = self._run_case(Flow)
                self.assertTrue(outcome.wasSuccessful())
                self.assertEqual(len(Flow._benchmark_results), 2)
                for result in Flow._benchmark_results:
                    self.assertEqual(result.rounds, 2)
                    self.assertEqual([sample['select'] for sample in result.samples], [1, 1])

    def test_block_names_are_valid_and_globally_unique(self):
        for outer, names in (
            ('parent', ('same', 'same')),
            ('parent', ('parent',)),
            (None, ('child',)),
            ('parent', (None,)),
            ('parent', ('invalid name',)),
        ):
            class Flow(BenchmarkCase):
                warmups = 0
                rounds = 1
                collectors = ('sql',)

                def test_flow(self):
                    with self.measure(outer):
                        for name in names:
                            with self.measure(name):
                                pass

            case = self._make_case(Flow)
            with self.subTest(outer=outer, names=names), self.assertRaises(ValueError):
                case._callTestMethod(case.test_flow)

            self.assertFalse(Flow._benchmark_results)
            self.assertIsNone(case._benchmark_current_round)

        with self.assertRaisesRegex(ValueError, 'active benchmark round'):
            case.measure()

    def test_nesting_must_match_even_when_names_and_order_match(self):
        for warmups in (0, 1):
            class Flow(BenchmarkCase):
                rounds = 2
                calls = 0

                def test_flow(self):
                    self.calls += 1
                    with self.measure('parent'):
                        if self.calls == 1:
                            with self.measure('child'):
                                self.cr.execute('SELECT 1')
                    if self.calls > 1:
                        with self.measure('child'):
                            self.cr.execute('SELECT 1')

            Flow.warmups = warmups
            case = self._make_case(Flow)
            with self.subTest(warmups=warmups), self.assertRaisesRegex(ValueError, 'scopes changed'):
                case._callTestMethod(case.test_flow)
            self.assertFalse(Flow._benchmark_results)
            self.assertIsNone(case._benchmark_current_round)
        self.stats_log.assert_not_called()

    def test_collector_start_failure_restores_round_state(self):
        with patch.dict(Collector._registry):
            class Broken(Collector):
                name = 'test_start_failure'
                start_order = 20
                metrics = (Metric('broken'),)

                def start(self):
                    msg = 'collector start failed'
                    raise ValueError(msg)

            class Flow(BenchmarkCase):
                warmups = 0
                rounds = 1
                collectors = ('sql', 'test_start_failure')

                def test_flow(self):
                    self.fail('workload must not run after a collector failure')

            case = self._make_case(Flow)
            with self.assertRaisesRegex(ValueError, 'collector start failed'):
                case._callTestMethod(case.test_flow)
        self.assertIsNone(case._benchmark_current_round)
        self.assertFalse(self.cr.query_hooks)
        self.assertEqual((self.record.value, self.record.double), (7, 14))
        self.assertFalse(Flow._benchmark_results)
        self.stats_log.assert_not_called()

    def test_workload_and_flush_errors_restore_round_state(self):
        record = self.record
        callbacks = list(self.cr.postcommit._funcs)

        def fail():
            msg = 'workload failed'
            raise ValueError(msg)

        for stage in ('preparation', 'block', 'flush', 'whole_method_flush'):
            class Flow(BenchmarkCase):
                warmups = 0
                rounds = 2
                calls = 0

                def test_flow(self):
                    self.calls += 1
                    self.cr.postcommit.add(lambda: None)
                    record.value = 9
                    if stage == 'preparation' and self.calls == 2:
                        fail()
                    if stage == 'whole_method_flush':
                        if self.calls == 2:
                            self.cr.precommit.add(fail)
                        return
                    with self.measure('parent'):
                        with self.measure('child'):
                            record.value = 10
                            if stage == 'block' and self.calls == 2:
                                fail()
                            if self.calls == 2:
                                self.cr.precommit.add(fail)

            case = self._make_case(Flow)
            with self.subTest(stage=stage), self.assertRaisesRegex(ValueError, 'workload failed'):
                case._callTestMethod(case.test_flow)
            self.assertFalse(Flow._benchmark_results)
            self.assertIsNone(case._benchmark_current_round)
            self.assertEqual((record.value, record.double), (7, 14))
            self.assertEqual(list(self.cr.postcommit._funcs), callbacks)
        self.stats_log.assert_not_called()

    def test_failed_user_does_not_prevent_the_next_user_from_running(self):
        new_test_user(self.env, login='benchmark_user')
        calls = []

        class Flow(BenchmarkCase):
            warmups = 1
            rounds = 2
            collectors = ('sql',)

            @users('admin', 'benchmark_user')
            def test_flow(self):
                calls.append((self.env.user.login, self.warm))
                self.cr.execute('SELECT 1')
                if self.env.user.login == 'admin' and self.warm:
                    with self.subTest():
                        self.fail('first user failure')

        with mute_logger(__name__):
            case, outcome = self._run_case(Flow)
        self.assertEqual(outcome.failures_count, 1)
        self.assertEqual(calls, [('admin', False), ('admin', True),
                                 ('benchmark_user', False), ('benchmark_user', True), ('benchmark_user', True)])
        result, = Flow._benchmark_results
        self.assertTrue(result.key.endswith('@benchmark_user'))
        self.assertEqual(result.rounds, 2)
        self.assertEqual(case.uid, self.uid)

    def test_users_preserve_other_decorators(self):
        new_test_user(self.env, login='benchmark_user')
        flag = SimpleNamespace(enabled=False)
        for outer_patch in (False, True):
            calls = []

            class Flow(BenchmarkCase):
                warmups = 0
                rounds = 2
                collectors = ('sql',)

                def test_flow(self):
                    self.assertTrue(flag.enabled)
                    login = self.env.user.login
                    calls.append(login)
                    with self.measure('query'):
                        for _ in range(1 if login == 'admin' else 2):
                            self.cr.execute('SELECT 1')

            decorate = patch.object(flag, 'enabled', True)
            if outer_patch:
                Flow.test_flow = decorate(users('admin', 'benchmark_user')(Flow.test_flow))
            else:
                Flow.test_flow = users('admin', 'benchmark_user')(decorate(Flow.test_flow))
            with self.subTest(outer_patch=outer_patch):
                _, outcome = self._run_case(Flow)
                self.assertTrue(outcome.wasSuccessful())
                self.assertEqual(calls, ['admin', 'admin', 'benchmark_user', 'benchmark_user'])
                self.assertEqual([result.key.rsplit('@', 1)[1] for result in Flow._benchmark_results], ['admin', 'benchmark_user'])
                self.assertEqual([result.metrics['queries'] for result in Flow._benchmark_results], [1, 2])
                self.assertFalse(flag.enabled)

    def test_skip_or_failed_subtest_does_not_publish_partial_results(self):
        for failure in ('skip', 'subtest'):
            class Flow(BenchmarkCase):
                warmups = 0
                rounds = 2
                calls = 0

                def test_flow(self):
                    self.calls += 1
                    if self.calls == 1:
                        return
                    if failure == 'skip':
                        msg = 'missing fixture'
                        raise SkipTest(msg)
                    with self.subTest():
                        self.fail('failed subtest')

            with self.subTest(failure=failure), mute_logger(__name__):
                _, outcome = self._run_case(Flow)
            self.assertEqual(outcome.skipped if failure == 'skip' else outcome.failures_count, 1)
            self.assertFalse(Flow._benchmark_results)
        self.stats_log.assert_not_called()


@tagged('standard', '-benchmark')
class TestBenchmarkHttp(BenchmarkCase, HttpCase):
    """Exercise real HTTP helpers, transactions and invocation on the mixed class."""
    warmups = 1
    rounds = 2
    collectors = ('sql',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.record = cls.env['test_testing_utilities.benchmark'].create({'value': 7})
        cls.enterClassContext(patch('odoo.tests.benchmark.reporting._logger_stats.info'))

        class BenchmarkController(Controller):
            @route('/test_tests/benchmark', type='http', auth='public', sitemap=False)
            def operation(self, record_id, fail=False):
                cr = request.env.cr
                cr.execute('SELECT value FROM test_testing_utilities_benchmark WHERE id = %s', [int(record_id)])
                value, = cr.fetchone()
                if value != 7:
                    msg = 'HTTP round did not start from its fixtures'
                    raise AssertionError(msg)
                cr.execute('UPDATE test_testing_utilities_benchmark SET value = 9 WHERE id = %s', [int(record_id)])
                if fail:
                    from werkzeug.exceptions import BadRequest  # noqa: PLC0415
                    msg = 'benchmark request failure'
                    raise BadRequest(msg)
                cr.execute('INSERT INTO test_testing_utilities_benchmark (value) VALUES (1) RETURNING id')
                created_id, = cr.fetchone()
                cr.execute('DELETE FROM test_testing_utilities_benchmark WHERE id = %s', [created_id])
                return 'done'

        cls.env.transaction.invalidate_ormcache('routing')
        cls.addClassCleanup(cls.env.transaction.invalidate_ormcache, 'routing')

    def test_http_queries_and_rollback(self):
        self.assertEqual(self.record.value, 7)
        with self.measure('request'):
            with self.measure('http'):
                response = self.url_open(f'/test_tests/benchmark?record_id={self.record.id}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, 'done')
        # A direct query after the request shares the measurement's SQL observer.
        with self.measure('direct'):
            self.cr.execute('SELECT 1')

    def test_failed_request(self):
        with self.measure('failed_request'):
            response = self.url_open(f'/test_tests/benchmark?record_id={self.record.id}&fail=1')
            self.assertEqual(response.status_code, 400)

    def tearDown(self):
        try:
            results = [result for result in self._benchmark_results if f'.{self._testMethodName}#' in result.key]
            self.assertTrue(results)
            self.assertTrue(all(result.rounds == 2 for result in results))
            self.assertEqual(self.record.value, 7)
            self.assertFalse(self.cr.query_hooks)
            self.assertFalse(any(isinstance(getattr(hook, '__self__', None), QueryCollector)
                                 for hook in getattr(threading.current_thread(), 'query_hooks', ())))
            if self._testMethodName == 'test_http_queries_and_rollback':
                parent, http, direct = results
                self.assertEqual(parent.metrics['queries'], http.metrics['queries'])
                self.assertGreater(http.metrics['select'], 0)
                self.assertGreaterEqual(http.metrics['update'], 1)
                self.assertGreaterEqual(http.metrics['insert'], 1)
                self.assertGreaterEqual(http.metrics['delete'], 1)
                self.assertGreater(http.metrics['sql_s'], 0)
                self.assertEqual(direct.metrics['queries'], 1)
        finally:
            super().tearDown()
