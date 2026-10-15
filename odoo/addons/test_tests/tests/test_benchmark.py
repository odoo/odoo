import json
import logging
import os
import random
import re
import statistics
import subprocess
import sys
import threading
from contextlib import ExitStack, contextmanager, redirect_stderr
from dataclasses import replace
from io import StringIO
from pathlib import Path
from textwrap import dedent
from types import ModuleType
from unittest import SkipTest, TestCase
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

from odoo import api, sql_db
from odoo.cli.benchmark import (
    Benchmark,
    build_benchmark_suite,
    get_benchmark_modules,
)
from odoo.tests import (
    BaseCase,
    BenchmarkCase,
    TransactionCase,
    benchmark,
    loader,
    tagged,
    users,
    warmup,
)
from odoo.tests.benchmark.case import Round, RoundMode
from odoo.tests.benchmark.collectors import (
    COLLECTORS,
    Aggregation,
    CPUCollector,
    Metric,
    QueryCollector,
    WallCollector,
    collect,
)
from odoo.tests.benchmark.reporting import Result, format_results_table
from odoo.tests.case import _Outcome
from odoo.tests.common import (
    BlockedRequest,
    _preserve_cursor_callbacks,
    new_test_user,
    requests,
)
from odoo.tests.loader import get_test_modules
from odoo.tests.result import OdooTestResult
from odoo.tests.tag_selector import TagsSelector
from odoo.tools import config
from odoo.tools.config import configmanager


def make_sample(**values):
    sample = {metric.key: 0 for collector in COLLECTORS for metric in collector.metrics}
    sample.update(values)
    return sample


class TestBenchmarkDiscovery(BaseCase):
    def test_package_exports_and_metric_defaults(self):
        # Read exports when the test runs so an earlier import cannot hide
        # a public name accidentally replaced while loading other modules.
        from odoo.tests import benchmark as public_decorator  # noqa: PLC0415
        from odoo.tests.benchmark import __all__ as exports  # noqa: PLC0415

        self.assertEqual(exports, ['BenchmarkCase', 'benchmark'])
        self.assertIs(public_decorator, benchmark)
        metric = Metric('count', 'count')
        self.assertEqual((metric.unit, metric.precision, metric.show_range), ('', 0, False))
        with self.assertRaises(TypeError):
            Metric('count', 'count', 'ms', 1)

    def test_round_mode_normalizes_strings(self):
        for mode in RoundMode:
            with self.subTest(mode=mode):
                self.assertIs(Round(Mock(), mode=mode).mode, mode)
                self.assertIs(Round(Mock(), mode=mode.value).mode, mode)
        with self.assertRaises(ValueError):
            Round(Mock(), mode='invalid')

    def test_invalid_decorator_combinations(self):
        def flow(self):
            pass

        with self.assertRaisesRegex(ValueError, '@users must be outside'):
            benchmark(users('admin')(flow))
        with self.assertRaisesRegex(ValueError, '@warmup cannot be combined'):
            benchmark(warmup(flow))
        with self.assertRaisesRegex(ValueError, '@warmup cannot be combined'):
            warmup(benchmark(flow))

    def test_unrestricted_filenames_and_explicit_imports(self):
        modules = list(get_benchmark_modules('test_tests'))
        self.assertIn('odoo.addons.test_tests.benchmarks.probe', [module.__name__ for module in modules])
        self.assertNotIn('odoo.addons.test_tests.benchmarks.unimported', sys.modules)
        suite = build_benchmark_suite({'test_tests'}, TagsSelector('benchmark', {'test_tests'}, default_tag='benchmark', strict=True))
        self.assertEqual([case._testMethodName for case in suite], ['blocks', 'ping'])
        self.assertTrue(all(type(case).__name__ == 'Probe' for case in suite))

    def test_normal_discovery_does_not_import_benchmarks(self):
        # A subprocess gives this assertion a clean import state.
        addons_path = config.format('addons_path', config['addons_path'])
        source = dedent(f"""
            import sys

            from odoo.tools import config

            config.parse_config(['--addons-path=' + {addons_path!r}], setup_logging=False)
            # Test framework imports need parsed configuration and addon paths.
            from odoo.tests.loader import get_test_modules

            get_test_modules('sale')
            assert 'odoo.addons.sale.benchmarks' not in sys.modules
        """)
        process = subprocess.run(
            [sys.executable, '-c', source], cwd=Path(__file__).parents[4],
            check=False, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertTrue(all('.benchmarks' not in module.__name__ for module in get_test_modules('test_tests')))

    def test_ownership_inheritance_overrides_and_order(self):
        module = ModuleType('odoo.addons.test_tests.benchmarks.arbitrary')

        class Parent(BenchmarkCase):
            @benchmark
            def inherited(self):
                pass

        class Direct(Parent):
            @users('admin')
            @benchmark
            def flow(self):
                pass

        class Inherited(Parent):
            allow_inherited_tests_method = True
            test_sequence = -1

            def inherited(self):
                pass

            @benchmark
            def first(self):
                pass

            @benchmark
            def second(self):
                pass

        class OptIn(Parent):
            allow_inherited_tests_method = True

        for cls in (Direct, Inherited, OptIn):
            cls.__module__ = module.__name__
            setattr(module, cls.__name__, cls)
        module.foreign = Parent
        module.alias = Direct
        with patch('odoo.cli.benchmark.get_benchmark_modules', return_value=[module]):
            suite = build_benchmark_suite({'test_tests'}, TagsSelector('benchmark', default_tag='benchmark', strict=True))
        self.assertEqual([(type(case).__name__, case._testMethodName) for case in suite], [
            ('Inherited', 'first'), ('Inherited', 'second'), ('Direct', 'flow'), ('OptIn', 'inherited'),
        ])

    def test_selectors(self):
        installed = {'test_tests', 'sale'}
        for spec, count in (
            (None, 2),
            ('/test_tests', 2),
            ('-/sale', 2),
            ('*', 5),
            ('standard', 0),
            ('/test_tests:Probe.ping', 1),
            ('-/test_tests:Probe.ping', 1),
        ):
            with self.subTest(spec=spec):
                selector = TagsSelector(spec or 'benchmark', installed, default_tag='benchmark', strict=True)
                self.assertEqual(build_benchmark_suite({'test_tests'}, selector).countTestCases(), count)

        self.assertIn(('standard', 'test_tests', None, None, None), TagsSelector('/test_tests').include)
        selector = TagsSelector('/test_tests:Probe.ping[a,b],-/sale', installed, default_tag='benchmark', strict=True)
        self.assertEqual(next(iter(selector.parameters))[1], ('+', 'a,b'))
        self.assertIn(('standard', None, None, None, None), TagsSelector('-/sale', installed).include)
        for spec, expected in (
            (r'/test_tests:Probe.ping[a\[b\],c],-/sale', 'a[b],c'),
            (r'/test_tests:Probe.ping[a\]b,c]', 'a]b,c'),
        ):
            with self.subTest(spec=spec):
                selector = TagsSelector(spec, installed, default_tag='benchmark', strict=True)
                self.assertEqual(next(iter(selector.parameters))[1], ('+', expected))

        for spec in ('/unknown', '-/unknown', 'bad tag', '/test_tests[unclosed', '/test_tests]'):
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                TagsSelector(spec or 'benchmark', installed, default_tag='benchmark', strict=True)

        with self.assertRaisesRegex(ValueError, 'unknown or not installed'):
            TagsSelector('/test_tests', set(), default_tag='benchmark', strict=True)

    def test_position_and_tags(self):
        module = ModuleType('odoo.addons.test_tests.benchmarks.positions')

        @tagged('slow')
        class Slow(BenchmarkCase):
            @benchmark
            def flow(self):
                pass

        @tagged('at_install', '-post_install')
        class AtInstall(Slow):
            allow_inherited_tests_method = True

        for cls in (Slow, AtInstall):
            cls.__module__ = module.__name__
            setattr(module, cls.__name__, cls)
        with patch('odoo.cli.benchmark.get_benchmark_modules', return_value=[module]):
            suite = build_benchmark_suite({'test_tests'}, TagsSelector('slow', default_tag='benchmark', strict=True))
        self.assertEqual([type(case).__name__ for case in suite], ['Slow'])
        self.assertEqual(Slow.test_tags, {'benchmark', 'post_install', 'slow'})
        self.assertFalse(Slow._retry)

    def test_http_blocker_and_class_cleanup(self):
        class Flow(BenchmarkCase):
            pass

        original = requests.sessions.Session.send
        with patch.object(TransactionCase, 'setUpClass'):
            try:
                Flow.setUpClass()
                self.assertIsNot(requests.sessions.Session.send, original)
                request = requests.Request('GET', 'https://benchmark.invalid').prepare()
                with self.assertRaises(BlockedRequest):
                    requests.Session().send(request)
            finally:
                Flow.doClassCleanups()
        self.assertIs(requests.sessions.Session.send, original)


class TestBenchmarkCollection(BaseCase):
    def test_collector_registration(self):
        names = [collector.name for collector in COLLECTORS]
        self.assertEqual(len(names), len(set(names)))
        metrics = [metric for collector in COLLECTORS for metric in collector.metrics]
        keys = [metric.key for metric in metrics]
        self.assertEqual(len(keys), len(set(keys)))
        for collector in COLLECTORS:
            self.assertRegex(collector.name, r'^[A-Za-z0-9_.-]+$')
            self.assertIs(type(collector.start_order), int)
            self.assertIsInstance(collector.metrics, tuple)
            self.assertTrue(collector.metrics)
        for metric in metrics:
            self.assertIsInstance(metric, Metric)
            self.assertRegex(metric.key, r'^[A-Za-z0-9_.-]+$')
            self.assertTrue(metric.label.strip())
            self.assertIsInstance(metric.unit, str)
            self.assertIs(type(metric.precision), int)
            self.assertGreaterEqual(metric.precision, 0)
            self.assertIs(type(metric.show_range), bool)

    def test_successful_measurement_inside_exception_handler(self):
        hooks = list(getattr(threading.current_thread(), 'query_hooks', ()))
        for use_block in (False, True):
            with self.subTest(use_block=use_block):
                state = Round(Mock(), mode=RoundMode.MEASURE)
                try:
                    msg = 'Handled preparation error'
                    raise ValueError(msg)  # noqa: TRY301 - exercise measurement inside a handled exception
                except ValueError:
                    metrics = state.start()
                    if use_block:
                        with state.measure(None):
                            pass
                        metrics = state.values[None]
                    else:
                        state.stop()
                self.assertEqual(metrics.keys(), make_sample().keys())
                self.assertEqual(threading.current_thread().query_hooks, hooks)

    def test_collector_lifecycle(self):
        events = []

        class Outer:
            name = 'outer'
            start_order = 10
            metrics = (Metric('outer', 'outer'),)

            def start(self):
                events.append('start ' + self.name)

            def stop(self):
                events.append('stop ' + self.name)
                return {self.name: 1}

            def aggregate(self, samples):
                return Aggregation({self.name: statistics.median(sample[self.name] for sample in samples)})

        class Inner(Outer):
            name = 'inner'
            metrics = (Metric('inner', 'inner'),)

        with patch('odoo.tests.benchmark.collectors.COLLECTORS', (Outer, Inner)):
            with collect() as values:
                events.append('body')

        self.assertEqual(events, ['start outer', 'start inner', 'body', 'stop inner', 'stop outer'])
        self.assertEqual(values, {'inner': 1, 'outer': 1})

        events.clear()
        with patch('odoo.tests.benchmark.collectors.COLLECTORS', (Inner, Outer)), collect():
            events.append('body')

        self.assertEqual(events, ['start inner', 'start outer', 'body', 'stop outer', 'stop inner'])
        for failure in ('start', 'stop', 'body'):
            with self.subTest(failure=failure):
                events.clear()

                def fail(collector):
                    events.append(failure + ' ' + collector.name)
                    raise ValueError(failure + ' failure')

                with ExitStack() as stack:
                    stack.enter_context(patch('odoo.tests.benchmark.collectors.COLLECTORS', (Outer, Inner)))
                    if failure != 'body':
                        stack.enter_context(patch.object(Inner, failure, fail))
                    with self.assertRaisesRegex(ValueError, failure + ' failure'), collect():
                        events.append('body')
                        if failure == 'body':
                            msg = 'body failure'
                            raise ValueError(msg)

                expected = ['start outer', 'start inner']
                if failure != 'start':
                    expected += ['body', 'stop inner']

                self.assertEqual(events, [*expected, 'stop outer'])

    def test_observers_start_before_timers_and_wall_is_innermost(self):
        self.assertEqual((QueryCollector.start_order, CPUCollector.start_order, WallCollector.start_order), (10, 90, 100))
        events = []
        hooks = list(getattr(threading.current_thread(), 'query_hooks', ()))
        with ExitStack() as stack:
            # Execution follows start_order, while reporting follows registration.
            stack.enter_context(patch('odoo.tests.benchmark.collectors.COLLECTORS', (WallCollector, QueryCollector, CPUCollector)))
            for collector in COLLECTORS:
                for operation in ('start', 'stop'):
                    original = getattr(collector, operation)

                    def record(instance, original=original, operation=operation):
                        events.append(operation + ' ' + instance.name)
                        return original(instance)

                    stack.enter_context(patch.object(collector, operation, record))
            with collect() as values:
                events.append('body')
            result = Result('benchmark/test_tests:Flow.run', [values])
        self.assertEqual(events, ['start queries', 'start cpu', 'start wall', 'body', 'stop wall', 'stop cpu', 'stop queries'])
        self.assertEqual(threading.current_thread().query_hooks, hooks)
        self.assertEqual([metric.key for metric in result.descriptions], [
            metric.key for collector in (WallCollector, QueryCollector, CPUCollector) for metric in collector.metrics
        ])

    def test_wall_timing_must_start_last(self):
        for start_order in (100, 101):
            with self.subTest(start_order=start_order):
                late = type('Late', (), {
                    'name': 'late', 'start_order': start_order, 'metrics': (Metric('late', 'late'),), 'start': Mock(),
                })
                with patch('odoo.tests.benchmark.collectors.COLLECTORS', (WallCollector, late)), \
                     patch.object(WallCollector, 'start') as start, self.assertRaisesRegex(ValueError, 'Wall timing must start last'), collect():
                    self.fail('Invalid ordering must be rejected before measuring')
                start.assert_not_called()
                late.start.assert_not_called()

    def test_invalid_collector_values_do_not_leak_query_hooks(self):
        # Bad collector output must fail the round without leaving SQL hooks
        # installed: those hooks would count queries from later benchmarks.
        class Broken:
            name = 'broken'
            start_order = 10
            metrics = (Metric('value', 'value'),)

            def start(self):
                pass

            def stop(self):
                return returned

            def aggregate(self, samples):
                return Aggregation(returned)

        hooks = list(getattr(threading.current_thread(), 'query_hooks', ()))
        for returned in (None, {}, {'extra': 1}, {'value': 1, 'extra': 2}, {'value': True}, {'value': float('nan')}):
            with self.subTest(returned=returned), patch('odoo.tests.benchmark.collectors.COLLECTORS', (QueryCollector, Broken)):
                with self.assertRaisesRegex(ValueError, 'Metric keys|Invalid metric values'), collect():
                    pass
            self.assertEqual(threading.current_thread().query_hooks, hooks)

        returned = {'extra': 1}
        with patch('odoo.tests.benchmark.collectors.COLLECTORS', (Broken,)), self.assertRaisesRegex(ValueError, 'Metric keys'):
            Result('benchmark/test_tests:Broken.run', [{'value': 1}])

    def test_sql_classification_and_actual_completion_durations(self):
        collector = QueryCollector()
        collector.start()
        try:
            for query in (
                'SELECT 1',
                'INSERT INTO fixture VALUES (1)',
                'UPDATE fixture SET value=1 WHERE TRUE',
                'DELETE FROM fixture WHERE TRUE',
                'WITH fixture AS (SELECT 1) SELECT * FROM fixture',
            ):
                completed = collector.hook(None, query, None, 0, 10)
                completed(0.002)
        finally:
            values = collector.stop()
        self.assertEqual(values, {'sql_s': 0.010, 'queries': 5, 'select': 1, 'insert': 1, 'update': 1, 'delete': 1, 'other': 1})


class TestBenchmarkReporting(BaseCase):
    def test_consistent_breakdown_when_total_query_count_is_constant(self):
        first = make_sample(queries=10, select=10, wall_s=1)
        second = dict(first, select=0, insert=10, wall_s=3)
        result = Result('benchmark/test_tests:Flow.run', [first, second])
        self.assertEqual(result.metrics['wall_s'], 2)
        self.assertEqual(result.metrics['queries'], 10)
        self.assertEqual(result.metrics['select'], 10)
        self.assertEqual(result.metrics['insert'], 0)
        self.assertEqual(sum(result.metrics[kind] for kind in ('select', 'insert', 'update', 'delete', 'other')), 10)
        with self.assertLogs('odoo.benchmark', logging.WARNING) as logs:
            result.publish()
        self.assertIn('breakdown varies', logs.output[0])

    def test_timing_medians_and_query_round_in_statistics(self):
        samples = [
            make_sample(wall_s=0.001, cpu_s=0.003, sql_s=0.005, queries=5, select=1, insert=4),
            make_sample(wall_s=0.009, cpu_s=0.005, sql_s=0.007, queries=9, select=9),
        ]
        result = Result('benchmark/test_tests:Flow.run', samples)
        self.assertAlmostEqual(result.metrics['wall_s'], 0.005)
        self.assertAlmostEqual(result.metrics['cpu_s'], 0.004)
        self.assertAlmostEqual(result.metrics['sql_s'], 0.006)
        self.assertEqual(result.metrics['queries'], 5)
        self.assertEqual(result.metrics['select'], 1)
        self.assertEqual(result.metrics['insert'], 4)
        with self.assertLogs('odoo.benchmark', logging.INFO) as logs:
            result.publish()
        line = f'{logs.records[0].name}: {logs.records[0].getMessage()}'
        regex = r'odoo\.benchmark\.stats: benchmark (?P<key>\S+) .*?\bqueries=(?P<value>\d+)'
        self.assertEqual(re.search(regex, line + ' future_metric=123').groupdict(), {'key': result.key, 'value': '5'})
        self.assertIn('wall_s=0.005 cpu_s=0.004 sql_s=0.006 queries=5', line)
        self.assertIn('varies', logs.output[1])

    def test_markdown_table_alignment_and_optional_ranges(self):
        samples = [make_sample(wall_s=0.001), make_sample(wall_s=0.009)]
        repeated = Result('benchmark/test_tests:Flow.run', samples)
        single = Result('benchmark/test_tests:Flow.single', samples[:1])
        lines = format_results_table([repeated, single]).splitlines()
        self.assertTrue(all(line.startswith('| ') and line.endswith(' |') for line in lines))
        positions = [[match.start() for match in re.finditer(r'\|', line)] for line in lines]
        self.assertTrue(all(position == positions[0] for position in positions))
        self.assertTrue(all(set(cell.strip()) == {'-'} for cell in lines[1].split('|')[1:-1]))
        headers = [cell.strip() for cell in lines[0].split('|')[1:-1]]
        cells = [cell.strip() for cell in lines[-1].split('|')[1:-1]]
        self.assertEqual(cells[headers.index('wall s min-max')], '-')
        self.assertIn('0.001-0.009', lines[2])
        self.assertNotIn('min-max', format_results_table([single]))

    def test_class_teardown_logs_the_result_table(self):
        class Reporting(BenchmarkCase):
            pass

        Reporting._benchmark_results = [Result('benchmark/test_tests:Flow.run', [make_sample()])]
        with self.assertLogs('odoo.benchmark', logging.INFO) as logs:
            Reporting.tearDownClass()
        self.assertIn('Reporting', logs.output[0])
        self.assertIn('| key', logs.output[0])
        self.assertIn('SELECT', logs.output[0])
        self.assertIn('other', logs.output[0])

    def test_table_flattens_multiline_labels(self):
        with patch.object(WallCollector, 'metrics', (replace(WallCollector.metrics[0], label='wall\ncost'),)):
            table = format_results_table([Result('benchmark/test_tests:Flow.single', [make_sample()])])
        self.assertIn('wall cost s', table)
        self.assertNotIn('<br>', table)
        self.assertEqual(len(table.splitlines()), 3)

    def test_statistics_preserve_large_integer_counts(self):
        large = 2**53 + 1
        result = Result('benchmark/test_tests:Flow.large', [make_sample(queries=large, select=large)])
        with self.assertLogs('odoo.benchmark.stats', logging.INFO) as logs:
            result.publish()
        self.assertIn(f'queries={large}', logs.output[0])

    def test_additional_collector_automatically_reports_its_metric(self):
        readings = iter((4.25, 8.75))

        class Payload:
            name = 'payload'
            start_order = 10
            metrics = (Metric('payload', 'payload', unit='KiB', precision=2, show_range=True),)

            def start(self):
                pass

            def stop(self):
                return {'payload': next(readings)}

            def aggregate(self, samples):
                return Aggregation({'payload': max(sample['payload'] for sample in samples)})

        samples = []
        with patch('odoo.tests.benchmark.collectors.COLLECTORS', (*COLLECTORS, Payload)):
            for _ in range(2):
                with collect() as values:
                    pass
                samples.append(values)
            result = Result('benchmark/test_tests:Flow.run', samples)
        self.assertEqual(result.metrics['payload'], 8.75)
        with self.assertLogs('odoo.benchmark.stats', logging.INFO) as logs:
            result.publish()
        self.assertIn('payload=8.75', logs.output[0])
        table = format_results_table([result])
        self.assertIn('payload KiB', table)
        self.assertIn('payload KiB min-max', table)
        self.assertIn('4.25-8.75', table)


class TestBenchmarkRounds(TransactionCase):
    def setUp(self):
        super().setUp()
        self.enterContext(patch.dict(config.options, benchmark_warmups=None, benchmark_rounds=None, benchmark_profile=False))
        # These tests run fake Flow benchmarks with unrelated workloads. Keep
        # their measurements out of the log used for real benchmark results.
        self.stats_log = self.enterContext(patch('odoo.tests.benchmark.reporting.stats_logger.info'))
        self.record = self.env['test_testing_utilities.benchmark'].create({'value': 7})

    def _case(self, cls, method='flow'):
        cls._benchmark_results = []
        case = cls(method)
        case.env, case.cr = self.env, self.cr
        case._benchmark_keys = {}
        return case

    def test_successful_round_inside_exception_handler(self):
        for use_block in (False, True):
            with self.subTest(use_block=use_block):
                class Flow(BenchmarkCase):
                    @benchmark(warmups=1, rounds=2)
                    def flow(self):
                        try:
                            msg = 'Handled preparation error'
                            raise ValueError(msg)  # noqa: TRY301 - exercise measurement inside a handled exception
                        except ValueError:
                            if use_block:
                                with self.measure():
                                    self.cr.execute('SELECT 1')
                            else:
                                self.cr.execute('SELECT 1')

                try:
                    msg = 'Handled caller error'
                    raise LookupError(msg)  # noqa: TRY301 - exercise round shutdown inside a handled exception
                except LookupError:
                    self._case(Flow).flow()
                result, = Flow._benchmark_results
                self.assertEqual(result.rounds, 2)
                self.assertEqual(result.metrics['queries'], 1)
                self.assertEqual(result.metrics['select'], 1)

    def test_rounds_preserve_application_randomness(self):
        values = []

        class Flow(BenchmarkCase):
            @benchmark(warmups=1, rounds=2)
            def flow(self):
                values.append(random.random())

        with patch('random.random', return_value=0.25) as generator:
            self._case(Flow).flow()
        self.assertEqual(values, [0.25] * 3)
        self.assertTrue(all(value < 1 for value in values))
        self.assertEqual(generator.call_count, 3)

    def test_round_defaults_precedence_and_validation(self):
        calls = []

        class Flow(BenchmarkCase):
            warmups = 2
            rounds = 4

            @benchmark(warmups=0, rounds=2)
            def flow(self):
                calls.append(self.warm)

        case = self._case(Flow)
        case.flow()
        self.assertEqual(calls, [True, True])
        calls.clear()
        with patch.dict(config.options, benchmark_warmups=1, benchmark_rounds=1):
            case = self._case(Flow)
            case.flow()
        self.assertEqual(calls, [False, True])
        for setting, value in (('warmups', -1), ('rounds', 0), ('rounds', True), ('rounds', 1.5)):
            with self.subTest(setting=setting, value=value):
                with patch.dict(config.options, {f'benchmark_{setting}': value}), self.assertRaisesRegex(ValueError, setting):
                    self._case(Flow).flow()

        class Defaults(BenchmarkCase):
            @benchmark
            def flow(self):
                calls.append(self.warm)

        calls.clear()
        self._case(Defaults).flow()
        self.assertEqual(calls, [False, True, True, True])

        Defaults.warmups, Defaults.rounds = 2, 1
        calls.clear()
        self._case(Defaults).flow()
        self.assertEqual(calls, [False, False, True])
        for source in ('decorator', 'class'):
            for setting, value in (('warmups', -1), ('rounds', 0), ('rounds', True), ('rounds', 1.5)):
                with self.subTest(source=source, setting=setting, value=value):
                    if source == 'decorator':
                        with patch.dict(Flow.flow._benchmark, {setting: value}), self.assertRaisesRegex(ValueError, setting):
                            self._case(Flow).flow()
                    else:
                        with patch.object(Defaults, setting, value), self.assertRaisesRegex(ValueError, setting):
                            self._case(Defaults).flow()

    def test_whole_and_unnamed_keys_query_counts_and_batches(self):
        class Whole(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                self.cr.execute('SELECT 1')

        case = self._case(Whole)
        case.flow()
        whole = Whole._benchmark_results[0]
        self.assertEqual(whole.metrics['queries'], 1)

        class Block(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                self.cr.execute('SELECT 0')
                with self.measure():
                    self.cr.executemany('SELECT %s', [(1,), (2,)])
                    self.cr.execute_values('SELECT * FROM (VALUES %s) AS values(v)', [(1,), (2,), (3,)], page_size=2)

        case = self._case(Block)
        case.flow()
        result = Block._benchmark_results[0]
        self.assertEqual(result.metrics['queries'], 4)
        self.assertEqual(result.metrics['select'], 4)
        self.assertEqual(result.key, 'benchmark/test_tests:Block.flow')
        self.assertNotIn('#', result.key)

    def test_chained_blocks_rollback_callbacks_and_cache_only_records(self):
        record = self.record
        seen = []

        class Flow(BenchmarkCase):
            @benchmark(warmups=1, rounds=2)
            def flow(self):
                seen.append(record.value)
                transient = self.env['test_testing_utilities.benchmark'].new({'value': 3})
                with self.measure('write'):
                    record.value = 11
                    self.cr.postcommit.add(lambda: None)
                    self.cr.postcommit.data['round'] = {'value': 11}
                    self.assertEqual(transient.value, 3)
                with self.measure('read'):
                    self.assertEqual(record.double, 22)

        case = self._case(Flow)
        funcs, data = tuple(self.cr.postcommit._funcs), self.cr.postcommit.data.copy()
        case.flow()
        self.assertEqual(seen, [7, 7, 7])
        self.assertEqual((record.value, record.double), (7, 14))
        self.assertEqual(tuple(self.cr.postcommit._funcs), funcs)
        self.assertEqual(self.cr.postcommit.data, data)
        self.assertEqual([item.key.rsplit('#', 1)[1] for item in Flow._benchmark_results], ['write', 'read'])

    def test_flush_boundaries(self):
        phases = []
        record = self.record

        class Flow(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                record.value = 8
                self.cr.precommit.add(lambda: phases.append(('prepare', bool(threading.current_thread().query_hooks))))
                with self.measure():
                    record.value = 9
                    self.cr.precommit.add(lambda: phases.append(('body', bool(threading.current_thread().query_hooks))))

        self._case(Flow).flow()
        self.assertEqual(phases, [('prepare', False), ('body', True)])
        self.assertEqual(record.value, 7)

    def test_whole_method_final_flush_is_measured_and_rolled_back(self):
        record = self.record
        phases = []

        class Whole(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                record.value = 9
                self.cr.precommit.add(lambda: phases.append(bool(threading.current_thread().query_hooks)))

        self._case(Whole).flow()
        self.assertEqual(phases, [True])
        self.assertEqual(Whole._benchmark_results[0].metrics['update'], 1)
        self.cr.execute('SELECT value FROM test_testing_utilities_benchmark WHERE id = %s', [record.id])
        self.assertEqual(self.cr.fetchone(), (7,))
        self.assertEqual((record.value, record.double), (7, 14))

    def test_cleanup_on_preparation_block_and_flush_errors(self):
        record = self.record

        def failed_flush():
            message = 'round failure'
            raise ValueError(message)

        for phase in ('prepare', 'entry', 'block', 'flush', 'final'):
            with self.subTest(phase=phase):
                class Flow(BenchmarkCase):
                    @benchmark(warmups=0, rounds=1)
                    def flow(self):
                        record.value = 9
                        self.cr.postcommit.data['failed'] = True
                        if phase == 'prepare':
                            failed_flush()
                        if phase == 'entry':
                            self.cr.precommit.add(failed_flush)
                        with self.measure():
                            record.value = 10
                            if phase == 'block':
                                failed_flush()
                            if phase == 'flush':
                                self.cr.precommit.add(failed_flush)
                        if phase == 'final':
                            self.cr.precommit.add(failed_flush)

                case = self._case(Flow)
                hooks = tuple(getattr(threading.current_thread(), 'query_hooks', ()))
                with self.assertRaisesRegex(ValueError, 'round failure'):
                    case.flow()
                self.assertEqual(record.value, 7)
                self.assertEqual(record.double, 14)
                self.assertFalse(self.env.transaction.field_dirty)
                self.assertFalse(self.env.transaction.tocompute)
                self.assertNotIn('failed', self.cr.postcommit.data)
                self.assertEqual(tuple(threading.current_thread().query_hooks), hooks)
                self.assertFalse(Flow._benchmark_results)

    def test_record_cache_cold_and_method_cache_warm(self):
        record = self.record
        misses = []

        @api.ormcache()
        def cached(self):
            misses.append(True)
            return 11

        class Flow(BenchmarkCase):
            @benchmark(warmups=1, rounds=2)
            def flow(self):
                self.assertNotIn(record.id, self.env.transaction.field_data.get(record._fields['value'], {}))
                self.assertEqual(record.value, 7)
                self.assertEqual(cached(record), 11)

        self._case(Flow).flow()
        self.assertEqual(misses, [True])

    def test_queries_on_another_cursor_are_collected(self):
        class Flow(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                with sql_db.db_connect(self.cr.dbname).cursor() as other:
                    with self.measure():
                        self.cr.execute('SELECT 1')
                        other.execute('SELECT 2')

        self._case(Flow).flow()
        self.assertEqual(Flow._benchmark_results[0].metrics['queries'], 2)

    def test_invalid_or_duplicate_region_names(self):
        for names in ((None, 'named'), ('named', None), ('same', 'same'), ('bad name',), ('',)):
            with self.subTest(names=names):
                class Flow(BenchmarkCase):
                    @benchmark(warmups=0, rounds=1)
                    def flow(self):
                        for name in names:
                            with self.measure(name):
                                pass

                case = self._case(Flow)
                with self.assertRaises(ValueError):
                    case.flow()
                self.assertFalse(Flow._benchmark_results)
                self.assertFalse(case._benchmark_keys)
                self.assertIsNone(case._benchmark_round)
                self.stats_log.assert_not_called()

    def test_nested_blocks_are_rejected(self):
        class Nested(BenchmarkCase):
            @benchmark
            def flow(self):
                with self.measure('outer'), self.measure('inner'):
                    pass

        case = self._case(Nested)
        with self.assertRaisesRegex(ValueError, 'nested'):
            case.flow()
        self.assertFalse(Nested._benchmark_results)
        self.assertFalse(case._benchmark_keys)
        self.assertIsNone(case._benchmark_round)
        self.stats_log.assert_not_called()

    def test_measure_requires_an_active_benchmark(self):
        case = BenchmarkCase()
        with self.assertRaisesRegex(ValueError, 'active'):
            with case.measure():
                pass
        self.assertFalse(case._benchmark_keys)
        self.assertIsNone(case._benchmark_round)
        self.stats_log.assert_not_called()

    def test_region_layout_must_match_between_executions(self):
        for warmups in (0, 1):
            class Changing(BenchmarkCase):
                executions = 0

                @benchmark(rounds=2)
                def flow(self):
                    self.executions += 1
                    for name in (('a', 'b') if self.executions == 1 else ('b', 'a')):
                        with self.measure(name):
                            self.cr.execute('SELECT 1')

            case = self._case(Changing)
            with patch.dict(config.options, benchmark_warmups=warmups), self.assertRaisesRegex(ValueError, 'regions changed'):
                case.flow()
            self.assertFalse(Changing._benchmark_results)
            self.assertFalse(case._benchmark_keys)
            self.assertIsNone(case._benchmark_round)
            self.stats_log.assert_not_called()

    def test_later_execution_failure_does_not_publish(self):
        class Failed(BenchmarkCase):
            executions = 0

            @benchmark(warmups=0, rounds=2)
            def flow(self):
                self.executions += 1
                self.cr.execute('SELECT 1')
                if self.executions == 2:
                    msg = 'later round failed'
                    raise ValueError(msg)

        case = self._case(Failed)
        with self.assertRaisesRegex(ValueError, 'later round failed'):
            case.flow()
        self.assertEqual(case.executions, 2)
        self.assertFalse(Failed._benchmark_results)
        self.assertFalse(case._benchmark_keys)
        self.stats_log.assert_not_called()

    def test_callback_snapshot_copies_nested_data_and_all_queues(self):
        callbacks = (self.cr.precommit, self.cr.postcommit, self.cr.prerollback, self.cr.postrollback)
        for callback in callbacks:
            callback.add(lambda: None)
            callback.data['baseline'] = {'values': [1]}
        funcs = [tuple(callback._funcs) for callback in callbacks]

        with _preserve_cursor_callbacks(self.cr):
            for callback in callbacks:
                callback.data['baseline']['values'].append(2)
        for callback in callbacks:
            self.assertEqual(callback.data['baseline'], {'values': [1]})

        def fail_with_modified_callbacks():
            with _preserve_cursor_callbacks(self.cr):
                for callback in callbacks:
                    callback.clear()
                    callback.data['baseline'] = {'values': [2]}
                msg = 'failure'
                raise ValueError(msg)

        # Odoo's assertion adds a savepoint that changes the queues being tested.
        TestCase.assertRaises(self, ValueError, fail_with_modified_callbacks)
        for callback, expected in zip(callbacks, funcs):
            self.assertEqual(tuple(callback._funcs), expected)
            self.assertEqual(callback.data['baseline'], {'values': [1]})

    def test_users_custom_names_and_duplicate_keys(self):
        login = 'sales team@example.com#%'
        new_test_user(self.env, login=login)

        class Flow(BenchmarkCase):
            @users(login)
            @benchmark(name='label', warmups=0, rounds=1)
            def flow(self):
                self.assertFalse(self.env.su)
                self.cr.execute('SELECT 1')

        case = self._case(Flow)
        case._outcome = _Outcome(case, OdooTestResult())
        case.flow()
        self.assertTrue(case._outcome.success)
        result = Flow._benchmark_results[0]
        self.assertEqual(result.key, 'benchmark/test_tests:Flow.flow#label@sales%20team%40example.com%23%25')
        self.assertTrue(case.env.su)
        with self.assertLogs(__name__, logging.ERROR):
            case.flow()
        self.assertEqual(case._outcome.result.errors_count, 1)
        self.assertEqual(len(Flow._benchmark_results), 1)
        for name in ('', 'white space', 'unicode-é', '#', True):
            with self.subTest(name=name), self.assertRaises(ValueError):
                benchmark(name=name)

    def test_multiple_users_have_independent_rounds_and_outcomes(self):
        logins = ('benchmark_first', 'benchmark_second')
        for login in logins:
            new_test_user(self.env, login=login)

        for fail_first in (False, True):
            with self.subTest(fail_first=fail_first):
                calls = []
                self.stats_log.reset_mock()

                class Flow(BenchmarkCase):
                    @users(*logins)
                    @benchmark(warmups=1, rounds=2)
                    def flow(self):
                        login = self.env.user.login
                        calls.append((login, self.warm))
                        self.cr.execute('SELECT 1')
                        if fail_first and login == logins[0] and self.warm:
                            with self.subTest():
                                self.fail('first user failure')

                case = self._case(Flow)
                original_env = case.env
                outcome = case._outcome = _Outcome(case, OdooTestResult())
                if fail_first:
                    with self.assertLogs(__name__, logging.ERROR):
                        case.flow()
                else:
                    case.flow()
                self.assertIs(case.env, original_env)
                self.assertIs(case._outcome, outcome)
                self.assertEqual(outcome.success, not fail_first)
                self.assertEqual(outcome.result.failures_count, int(fail_first))
                expected_first = [(logins[0], False), (logins[0], True)]
                if not fail_first:
                    expected_first.append((logins[0], True))
                self.assertEqual(calls, expected_first + [(logins[1], False), (logins[1], True), (logins[1], True)])
                expected_keys = [f'benchmark/test_tests:Flow.flow@{login}' for login in (logins[1:] if fail_first else logins)]
                self.assertEqual([result.key for result in Flow._benchmark_results], expected_keys)
                self.assertEqual(set(case._benchmark_keys), set(expected_keys))
                self.assertEqual([result.rounds for result in Flow._benchmark_results], [2] * len(expected_keys))
                self.assertEqual(self.stats_log.call_count, len(expected_keys))

    def test_profile_scope_extra_execution_and_failure(self):
        events = []
        profiles = []

        @contextmanager
        def profile(case, description, **kwargs):
            case.assertEqual(kwargs['init_frame'].f_code.co_name, '_round')
            profiles.append(description)
            events.append('start')
            yield Mock(profile_id=1)
            events.append('stop')

        class Flow(BenchmarkCase):
            @benchmark(warmups=0, rounds=2)
            def flow(self):
                events.append('prepare')
                with self.measure('a'):
                    events.append('a')
                with self.measure('b'):
                    events.append('b')

        with patch.dict(config.options, benchmark_profile=True), patch.object(Flow, 'profile', profile), \
             patch('odoo.tests.benchmark.case.sql_db.db_connect') as connection:
            connection.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = (1,)
            self._case(Flow).flow()
        self.assertEqual(events, ['prepare', 'a', 'b', 'prepare', 'a', 'b', 'prepare', 'start', 'a', 'stop', 'start', 'b', 'stop'])
        self.assertEqual(profiles, ['benchmark/test_tests:Flow.flow#a', 'benchmark/test_tests:Flow.flow#b'])
        self.assertEqual([result.rounds for result in Flow._benchmark_results], [2, 2])
        self.stats_log.reset_mock()
        with patch.dict(config.options, benchmark_profile=True), patch.object(Flow, 'profile') as fake:
            fake.return_value.__enter__.return_value.profile_id = None
            case = self._case(Flow)
            with self.assertRaisesRegex(RuntimeError, 'save benchmark profile'):
                case.flow()
        self.assertFalse(Flow._benchmark_results)
        self.assertFalse(case._benchmark_keys)
        self.stats_log.assert_not_called()

        with patch.dict(config.options, benchmark_profile=True), patch.object(Flow, 'profile') as fake, \
             patch('odoo.tests.benchmark.case.sql_db.db_connect') as connection:
            fake.return_value.__enter__.return_value.profile_id = 1
            connection.return_value.cursor.return_value.__enter__.return_value.fetchone.return_value = None
            case = self._case(Flow)
            with self.assertRaisesRegex(RuntimeError, 'save benchmark profile'):
                case.flow()
        self.assertFalse(Flow._benchmark_results)
        self.assertFalse(case._benchmark_keys)
        self.stats_log.assert_not_called()

    def test_profiles_survive_round_rollback(self):
        record = self.record
        executions = []

        class Flow(BenchmarkCase):
            @benchmark(warmups=1, rounds=2)
            def flow(self):
                executions.append(True)
                self.cr.execute("SELECT 'benchmark preparation'")
                with self.measure('a'):
                    self.cr.execute("SELECT 'benchmark a'")
                    record.value = 9
                with self.measure('b'):
                    self.cr.execute("SELECT 'benchmark b'")

        case = self._case(Flow)
        case.profile_session = uuid4().hex
        try:
            with patch.dict(config.options, benchmark_profile=True):
                case.flow()
            # A fresh cursor sees the profiler's committed rows after the round
            # savepoint rolled back; the test's repeatable-read snapshot cannot.
            with sql_db.db_connect(self.cr.dbname).cursor() as cr:
                cr.execute('SELECT name, sql FROM ir_profile WHERE session = %s ORDER BY id', [case.profile_session])
                profiles = cr.fetchall()
            self.assertEqual(len(profiles), 2)
            for (name, queries), label in zip(profiles, ('a', 'b')):
                self.assertTrue(name.endswith(f'benchmark/test_tests:Flow.flow#{label}'))
                statements = [entry.get('query') for entry in json.loads(queries)]
                self.assertIn(f"SELECT 'benchmark {label}'", statements)
                self.assertNotIn("SELECT 'benchmark preparation'", statements)
                self.assertNotIn(f"SELECT 'benchmark {'b' if label == 'a' else 'a'}'", statements)
            self.assertEqual(len(executions), 4)
            self.assertEqual([result.rounds for result in Flow._benchmark_results], [2, 2])
            self.assertEqual((record.value, record.double), (7, 14))
        finally:
            # Profile storage commits independently of the test transaction.
            with sql_db.db_connect(self.cr.dbname).cursor() as cr:
                cr.execute('DELETE FROM ir_profile WHERE session = %s', [case.profile_session])

    def test_region_consistency_includes_profiles_and_whole_body(self):
        for warmups in (0, 1):
            for profiling in (False, True):
                matching_rounds = warmups + 1 if profiling else 1

                class Changing(BenchmarkCase):
                    executions = 0

                    @benchmark(rounds=1)
                    def flow(self):
                        self.executions += 1
                        if self.executions <= matching_rounds:
                            with self.measure():
                                self.cr.execute('SELECT 1')

                with patch.dict(config.options, benchmark_warmups=warmups, benchmark_profile=profiling):
                    case = self._case(Changing)
                    self.stats_log.reset_mock()
                    if warmups or profiling:
                        with self.assertRaisesRegex(ValueError, 'regions changed'):
                            case.flow()
                        self.assertFalse(Changing._benchmark_results)
                        self.assertFalse(case._benchmark_keys)
                        self.stats_log.assert_not_called()
                    else:
                        case.flow()
                        self.assertEqual(len(Changing._benchmark_results), 1)

    def test_duplicate_keys_identify_benchmark_modules(self):
        @benchmark(warmups=0, rounds=1)
        def flow(case):
            case.cr.execute('SELECT 1')

        first = type('Flow', (BenchmarkCase,), {'__module__': 'odoo.addons.test_tests.benchmarks.one', 'flow': flow})
        second = type('Flow', (BenchmarkCase,), {'__module__': 'odoo.addons.test_tests.benchmarks.two', 'flow': flow})
        a, b = self._case(first), self._case(second)
        b._benchmark_keys = a._benchmark_keys
        a.flow()
        with self.assertRaisesRegex(ValueError, 'one.Flow.flow.*two.Flow.flow'):
            b.flow()
        self.assertFalse(second._benchmark_results)

    def test_skips_and_subtest_failures_do_not_publish(self):
        class Skipped(BenchmarkCase):
            @benchmark
            def flow(self):
                msg = 'missing data'
                raise SkipTest(msg)

        with self.assertRaises(SkipTest):
            self._case(Skipped).flow()
        self.assertFalse(Skipped._benchmark_results)

        class Failed(BenchmarkCase):
            @benchmark(warmups=0, rounds=1)
            def flow(self):
                with self.subTest():
                    self.fail('business failure')

        case = self._case(Failed)
        case._outcome = _Outcome(case, OdooTestResult())
        outcome = case._outcome
        for _ in range(2):
            with self.assertLogs(__name__, logging.ERROR):
                case.flow()
            self.assertIs(case._outcome, outcome)
            self.assertFalse(outcome.success)
            self.assertEqual(outcome.result.failures_count, 1)
            self.assertFalse(Failed._benchmark_results)
            self.assertFalse(case._benchmark_keys)


class TestBenchmarkCLI(BaseCase):
    def test_parse_options_requires_setup(self):
        with patch('odoo.cli.benchmark.config', configmanager()), \
             self.assertRaisesRegex(AssertionError, '_setup_options'):
            Benchmark()._parse_options([])

    def test_cli_argument_errors_before_startup(self):
        for args in (
            [],
            ['-d', 'a,b'],
            ['-d', 'a', '-u', 'sale'],
            ['-d', 'a', '-u', ''],
            ['-d', 'a', '--rounds', '0'],
            ['-d', 'a', '--warmups', '-1'],
            ['-d', 'a', '--rounds', '1.5'],
            ['-d', 'a', '-t', 'bad tag'],
        ):
            with self.subTest(args=args):
                fresh = configmanager()
                with patch('odoo.cli.benchmark.config', fresh), patch('odoo.cli.benchmark.Registry.new') as startup:
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                        Benchmark().run(['-c', '/dev/null', *args])
                    self.assertEqual(error.exception.code, 2)
                    startup.assert_not_called()

    def test_startup_failure_exit_status(self):
        with (
            self.assertLogs('odoo.benchmark', logging.ERROR),
            patch('odoo.cli.benchmark.config', configmanager()),
            patch('odoo.cli.benchmark.load_server_wide_modules'),
            patch.object(Benchmark, '_check_database_prepared'),
            patch('odoo.cli.benchmark.Registry.new', side_effect=ValueError('startup failure')),
        ):
            with self.assertRaises(SystemExit) as error:
                Benchmark().run(['-c', '/dev/null', '-d', 'a'])
        self.assertEqual(error.exception.code, 1)

    def test_startup_suppresses_discovery_and_restores_it(self):
        ordinary_make_suite = loader.make_suite
        for selector, startup_fails in ((None, False), ('*', False), ('*', True)):
            with self.subTest(selector=selector, startup_fails=startup_fails):
                fresh = configmanager()
                registry = MagicMock()
                env = MagicMock()
                env['ir.module.module'].search.return_value.mapped.return_value = ['test_tests']
                result = Mock(skipped=0)
                result.wasSuccessful.return_value = True

                def initialize(dbname, *, update_module):
                    self.assertTrue(fresh['test_enable'])
                    self.assertEqual(fresh['test_tags'], selector)
                    with patch.object(loader, 'get_test_modules') as discover:
                        self.assertEqual(loader.make_suite(['test_tests']).countTestCases(), 0)
                        discover.assert_not_called()
                    if startup_fails:
                        msg = 'startup failure'
                        raise ValueError(msg)
                    return registry

                def build_suite(installed, selected):
                    self.assertIs(loader.make_suite, ordinary_make_suite)
                    self.assertEqual(installed, {'test_tests'})
                    if selector is None:
                        self.assertEqual(selected.include, {('benchmark', None, None, None, None)})
                    return build_benchmark_suite(installed, selected)

                with (
                    self.assertLogs('odoo.benchmark', logging.INFO),
                    patch('odoo.cli.benchmark.config', fresh),
                    patch('odoo.cli.benchmark.load_server_wide_modules'),
                    patch.object(Benchmark, '_check_database_prepared'),
                    patch('odoo.cli.benchmark.Registry.new', side_effect=initialize) as startup,
                    patch('odoo.cli.benchmark.api.Environment', return_value=env),
                    patch('odoo.cli.benchmark.build_benchmark_suite', side_effect=build_suite),
                    patch.object(loader, 'run_suite', return_value=result),
                ):
                    with self.assertRaises(SystemExit) as error:
                        args = ['-c', '/dev/null', '-d', 'a']
                        if selector is not None:
                            args += ['-t', selector]
                        Benchmark().run(args)
                    self.assertEqual(error.exception.code, int(startup_fails))
                    startup.assert_called_once_with('a', update_module=False)
                self.assertIs(loader.make_suite, ordinary_make_suite)

    def test_database_preflight_rejects_pending_operations_before_registry(self):
        for state in ('to install', 'to upgrade', 'to remove'):
            with self.subTest(state=state):
                with (
                    self.assertLogs('odoo.benchmark', logging.ERROR) as logs,
                    patch('odoo.cli.benchmark.config', configmanager()),
                    patch('odoo.cli.benchmark.sql_db.db_connect') as connection,
                    patch('odoo.cli.benchmark.is_initialized', return_value=True),
                    patch('odoo.cli.benchmark.Registry.new') as startup,
                    patch('odoo.cli.benchmark.load_server_wide_modules') as load,
                ):
                    connection.return_value.cursor.return_value.__enter__.return_value.fetchall.return_value = [('sale', state)]
                    with self.assertRaises(SystemExit) as error:
                        Benchmark().run(['-c', '/dev/null', '-d', 'a'])
                    self.assertEqual(error.exception.code, 1)
                    startup.assert_not_called()
                    load.assert_not_called()
                self.assertIn(f'sale ({state})', logs.output[0])

    def test_database_preflight_rejects_uninitialized_database(self):
        with (
            patch('odoo.cli.benchmark.sql_db.db_connect') as connection,
            patch('odoo.cli.benchmark.is_initialized', return_value=False),
        ):
            with self.assertRaisesRegex(ValueError, 'not initialized'):
                Benchmark._check_database_prepared('a')
            connection.return_value.cursor.return_value.__enter__.return_value.execute.assert_not_called()

    def test_cli_execution_exit_status(self):
        for count, successful, skipped, status, message in (
            (0, True, 0, 1, 'No benchmarks matched'),
            (1, False, 0, 1, 'Running 1 selected benchmarks'),
            (1, True, 1, 0, 'All selected benchmarks were skipped'),
        ):
            with self.subTest(successful=successful, skipped=skipped, count=count):
                registry = MagicMock()
                env = MagicMock()
                env['ir.module.module'].search.return_value.mapped.return_value = ['test_tests']
                result = Mock(skipped=skipped)
                result.wasSuccessful.return_value = successful
                with (
                    self.assertLogs('odoo.benchmark', logging.INFO) as logs,
                    patch('odoo.cli.benchmark.config', configmanager()),
                    patch.object(Benchmark, '_check_database_prepared'),
                    patch('odoo.cli.benchmark.load_server_wide_modules'),
                    patch('odoo.cli.benchmark.Registry.new', return_value=registry),
                    patch('odoo.cli.benchmark.api.Environment', return_value=env),
                    patch('odoo.cli.benchmark.build_benchmark_suite', return_value=[Mock() for _ in range(count)]),
                    patch.object(loader, 'run_suite', return_value=result)
                ):
                    with self.assertRaises(SystemExit) as error:
                        Benchmark().run(['-c', '/dev/null', '-d', 'a', '-t', '/test_tests'])
                    self.assertEqual(error.exception.code, status)
                self.assertTrue(any(message in line for line in logs.output))

    def test_cli_in_existing_database(self):
        executable = Path(__file__).parents[4] / 'odoo-bin'
        common = [sys.executable, str(executable), 'benchmark', '-c', '/dev/null', '-d', config['db_name'][0],
                  '--addons-path=' + config.format('addons_path', config['addons_path']), '--warmups', '0', '--rounds', '1']
        # -c /dev/null isolates command options. Forward resolved connection
        # settings through libpq so the child still reaches the same database.
        env = os.environ.copy()
        for setting in ('host', 'port', 'user', 'password', 'sslmode'):
            value = config[f'db_{setting}']
            if value:
                env[f'PG{setting.upper()}'] = str(value)
        # Keep real-process coverage for successful execution and setup failure.
        # Selector, skip and exit-status combinations are tested in process.
        for selector, status, message in (
            ('/test_tests', 0, 'benchmark/test_tests:Probe.ping'),
            ('benchmark_cli_setup_error/test_tests', 1, 'Benchmark fixture setup failure'),
        ):
            with self.subTest(selector=selector):
                arguments = [*common, '-t', selector]
                process = subprocess.run(arguments, check=False, capture_output=True, text=True, timeout=90, env=env)
                self.assertEqual(process.returncode, status, process.stderr)
                self.assertIn(message, process.stderr)
                self.assertNotIn('Starting post tests', process.stderr)
                self.assertNotIn('Starting Test', process.stderr)
