# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
import difflib
import logging
import re
import sys
from contextlib import contextmanager
from pathlib import PurePath
from unittest import SkipTest, skip
from unittest.mock import patch

from odoo.tests.case import TestCase
from odoo.tests.common import BaseCase, TransactionCase, users, warmup
from odoo.tests.result import OdooTestResult

_logger = logging.getLogger(__name__)

from odoo.tests import MetaCase


if sys.version_info >= (3, 8):
    # this is mainly to ensure that simple tests will continue to work even if BaseCase should be used
    # this only works if doClassCleanup is available on testCase because of the vendoring of suite.py.
    # this test will only work in python 3.8 +
    class TestTestSuite(TestCase, metaclass=MetaCase):

        def test_test_suite(self):
            """ Check that OdooSuite handles unittest.TestCase correctly. """


class TestRunnerLoggingCommon(TransactionCase):
    """
    The purpose of this class is to do some "metatesting": it actually checks
    that on error, the runner logged the error with the right file reference.
    This is mainly to avoid having errors in test/common.py or test/runner.py`.
    This kind of metatesting is tricky; in this case the logs are made outside
    of the test method, after the teardown actually.
    """

    def setUp(self):
        self.expected_logs = None
        self.expected_first_frame_methods = None
        return super().setUp()

    def _addError(self, result, test, exc_info):
        # We use this hook to catch the logged error. It is initially called
        # post tearDown, and logs the actual errors. Because of our hack
        # tests.common._ErrorCatcher, the errors are logged directly. This is
        # still useful to test errors raised from tests. We cannot assert what
        # was logged after the test inside the test, though. This method can be
        # temporary renamed to test the real failure.
        try:
            self.test_result = result
            # while we are here, let's check that the first frame of the stack
            # is always inside the test method

            if exc_info:
                tb = exc_info[2]
                self._check_first_frame(tb)

            # intercept all ir_logging. We cannot use log catchers or other
            # fancy stuff because makeRecord is too low level.
            log_records = []

            def makeRecord(logger, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
                log_records.append({
                    'logger': logger, 'name': name, 'level': level, 'fn': fn, 'lno': lno,
                    'msg': msg % args, 'exc_info': exc_info, 'func': func, 'extra': extra, 'sinfo': sinfo,
                })

            def handle(logger, record):
                # disable error logging
                return

            fake_result = OdooTestResult()
            with patch('logging.Logger.makeRecord', makeRecord), patch('logging.Logger.handle', handle):
                super()._addError(fake_result, test, exc_info)

            self._check_log_records(log_records)

        except Exception as e:
            # we don't expect _feedErrorsToResult() to raise any exception, this
            # will make it more robust to future changes and eventual mistakes
            _logger.exception(e)

    def _check_first_frame(self, tb):
        """ Check that the first frame of the given traceback is the expected method name. """
        # the list expected_first_frame_methods allow to define a list of first
        # expected frame (useful for setup/teardown tests)
        if self.expected_first_frame_methods is None:
            expected_first_frame_method = self._testMethodName
        else:
            expected_first_frame_method = self.expected_first_frame_methods.pop(0)
        first_frame_method = tb.tb_frame.f_code.co_name
        if first_frame_method != expected_first_frame_method:
            self._log_error(f"Checking first tb frame: {first_frame_method} is not equal to {expected_first_frame_method}")

    def _check_log_records(self, log_records):
        """ Check that what was logged is what was expected. """
        for log_record in log_records:
            self._assert_log_equal(log_record, 'logger', _logger)
            self._assert_log_equal(log_record, 'name', 'odoo.addons.base.tests.test_test_suite')
            self._assert_log_equal(log_record, 'fn', __file__)
            self._assert_log_equal(log_record, 'func', self._testMethodName)

        if self.expected_logs is not None:
            for log_record in log_records:
                level, msg = self.expected_logs.pop(0)
                self._assert_log_equal(log_record, 'level', level)
                self._assert_log_equal(log_record, 'msg', msg)

    def _assert_log_equal(self, log_record, key, expected):
        """ Check the content of a log record. """
        value = log_record[key]
        if key == 'msg':
            value = self._clean_message(value)
        if value != expected:
            if key != 'msg':
                self._log_error(f"Key `{key}` => `{value}` is not equal to `{expected}` \n {log_record['msg']}")
            else:
                diff = '\n'.join(difflib.ndiff(expected.splitlines(), value.splitlines()))
                self._log_error(f"Key `{key}` did not matched expected:\n{diff}")

    def _log_error(self, message):
        """ Log an actual error (about a log in a test that doesn't match expectations) """
        # we would just log, but using the test_result will help keeping the tests counters correct
        self.test_result.addError(self, (AssertionError, AssertionError(message), None))

    def _clean_message(self, message):
        root_path = PurePath(__file__).parents[4]  # removes /odoo/addons/base/tests/test_test_suite.py
        python_path = PurePath(contextlib.__file__).parent  # /usr/lib/pythonx.x, C:\\python\\Lib, ...
        message = re.sub(r'line \d+', 'line $line', message)
        message = re.sub(r'py:\d+', 'py:$line', message)
        message = re.sub(r'decorator-gen-\d+', 'decorator-gen-xxx', message)
        message = re.sub(r'^\s*\^+\s*\n', '', message, flags=re.MULTILINE)
        message = message.replace(f'"{root_path}', '"/root_path/odoo')
        message = message.replace(f'"{python_path}', '"/usr/lib/python')
        message = message.replace('\\', '/')
        return message


class TestRunnerLogging(TestRunnerLoggingCommon):

    def test_has_add_error(self):
        self.assertTrue(hasattr(self, '_addError'))

    def test_raise(self):
        raise Exception('This is an error')

    def test_raise_subtest(self):
        """
        with subtest, we expect to have multiple errors, one per subtest
        """
        def make_message(message):
            return (
f'''ERROR: Subtest TestRunnerLogging.test_raise_subtest (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_raise_subtest
    raise Exception('{message}')
Exception: {message}
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, make_message('This is an error')),
        ]
        with self.subTest():
            raise Exception('This is an error')

        self.assertFalse(self.expected_logs, "Error should have been logged immediatly")

        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, make_message('This is an error2')),
        ]

        with self.subTest():
            raise Exception('This is an error2')

        self.assertFalse(self.expected_logs, "Error should have been logged immediatly")

    @users('__system__')
    @warmup
    def test_with_decorators(self):
        # note, this test may be broken with a decorator in decorator=5.0.5 since the behaviour changed
        # but decoratorx was not introduced yet.
        message = (
'''ERROR: Subtest TestRunnerLogging.test_with_decorators (login='__system__')
Traceback (most recent call last):
  File "<decorator-gen-xxx>", line $line, in test_with_decorators
  File "/root_path/odoo/odoo/tests/common.py", line $line, in _users
    func(*args, **kwargs)
  File "<decorator-gen-xxx>", line $line, in test_with_decorators
  File "/root_path/odoo/odoo/tests/common.py", line $line, in warmup
    func(*args, **kwargs)
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_with_decorators
    raise Exception('This is an error')
Exception: This is an error
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]
        raise Exception('This is an error')

    def test_traverse_contextmanager(self):
        @contextmanager
        def assertSomething():
            yield
            raise Exception('This is an error')

        with assertSomething():
            pass

    def test_subtest_sub_call(self):
        def func():
            with self.subTest():
                raise Exception('This is an error')

        func()

    def test_call_stack(self):
        message = (
'''ERROR: TestRunnerLogging.test_call_stack
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception('This is an error')
Exception: This is an error
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            gamma()

        def gamma():
            raise Exception('This is an error')

        alpha()

    def test_call_stack_context_manager(self):
        message = (
'''ERROR: TestRunnerLogging.test_call_stack_context_manager
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack_context_manager
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception('This is an error')
Exception: This is an error
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            with self.with_user('admin'):
                gamma()
                return 0

        def gamma():
            raise Exception('This is an error')

        alpha()

    def test_call_stack_subtest(self):
        message = (
'''ERROR: Subtest TestRunnerLogging.test_call_stack_subtest (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_call_stack_subtest
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    gamma()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in gamma
    raise Exception('This is an error')
Exception: This is an error
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            beta()

        def beta():
            with self.subTest():
                gamma()

        def gamma():
            raise Exception('This is an error')

        alpha()

    def test_assertQueryCount(self):
        message = (
'''FAIL: Subtest TestRunnerLogging.test_assertQueryCount (<subtest>)
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_assertQueryCount
    with self.assertQueryCount(system=0):
  File "/usr/lib/python/contextlib.py", line $line, in __exit__
    next(self.gen)
  File "/root_path/odoo/odoo/tests/common.py", line $line, in assertQueryCount
    self.fail(msg % (login, count, expected, funcname, filename, linenum))
AssertionError: Query count more than expected for user __system__: 1 > 0 in test_assertQueryCount at base/tests/test_test_suite.py:$line
''')
        if self._python_version < (3, 10, 0):
            message = message.replace("with self.assertQueryCount(system=0):", "self.env.cr.execute('SELECT 1')")

        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]
        with self.assertQueryCount(system=0):
            self.env.cr.execute('SELECT 1')

    @users('__system__')
    @warmup
    def test_assertQueryCount_with_decorators(self):
        with self.assertQueryCount(system=0):
            self.env.cr.execute('SELECT 1')

    def test_reraise(self):
        message = (
'''ERROR: TestRunnerLogging.test_reraise
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_reraise
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    raise Exception('This is an error')
Exception: This is an error
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            # pylint: disable=try-except-raise
            try:
                beta()
            except Exception:
                raise

        def beta():
            raise Exception('This is an error')

        alpha()

    def test_handle_error(self):
        message = (
'''ERROR: TestRunnerLogging.test_handle_error
Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    beta()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in beta
    raise Exception('This is an error')
Exception: This is an error

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in test_handle_error
    alpha()
  File "/root_path/odoo/odoo/addons/base/tests/test_test_suite.py", line $line, in alpha
    raise Exception('This is an error2')
Exception: This is an error2
''')
        self.expected_logs = [
            (logging.INFO, '=' * 70),
            (logging.ERROR, message),
        ]

        def alpha():
            try:
                beta()
            except Exception:
                raise Exception('This is an error2')

        def beta():
            raise Exception('This is an error')

        alpha()


class TestRunnerLoggingSetup(TestRunnerLoggingCommon):

    def setUp(self):
        super().setUp()
        self.expected_first_frame_methods = [
            'setUp',
            'cleanupError2',
            'cleanupError',
        ]

        def cleanupError():
            raise Exception("This is a cleanup error")
        self.addCleanup(cleanupError)

        def cleanupError2():
            raise Exception("This is a second cleanup error")
        self.addCleanup(cleanupError2)

        raise Exception('This is a setup error')

    def test_raises_setup(self):
        _logger.error("This shouldn't be executed")

    def tearDown(self):
        _logger.error("This shouldn't be executed since setup failed")


class TestRunnerLoggingTeardown(TestRunnerLoggingCommon):
    def setUp(self):
        super().setUp()
        self.expected_first_frame_methods = [
            'test_raises_teardown',
            'test_raises_teardown',
            'test_raises_teardown',
            'tearDown',
            'cleanupError2',
            'cleanupError',
        ]

        def cleanupError():
            raise Exception("This is a cleanup error")
        self.addCleanup(cleanupError)

        def cleanupError2():
            raise Exception("This is a second cleanup error")
        self.addCleanup(cleanupError2)

    def tearDown(self):
        raise Exception('This is a tearDown error')

    def test_raises_teardown(self):
        with self.subTest():
            raise Exception('This is a subTest error')
        with self.subTest():
            raise Exception('This is a second subTest error')
        raise Exception('This is a test error')


class TestSubtests(BaseCase):

    def test_nested_subtests(self):
        with self.subTest(a=1, x=2):
            with self.subTest(b=3, x=4):
                self.assertEqual(self._subtest._subDescription(), '(b=3, x=4, a=1)')
            with self.subTest(b=5, x=6):
                self.assertEqual(self._subtest._subDescription(), '(b=5, x=6, a=1)')


class TestClassSetup(BaseCase):

    @classmethod
    def setUpClass(cls):
        raise SkipTest('Skip this class')

    def test_method(self):
        pass


class TestClassTeardown(BaseCase):

    @classmethod
    def tearDownClass(cls):
        raise SkipTest('Skip this class')

    def test_method(self):
        pass


class Test01ClassCleanups(BaseCase):
    """
    The purpose of this test combined with Test02ClassCleanupsCheck is to check that
    class cleanup work. class cleanup where introduced in python3.8 but tests should
    remain compatible with python 3.7
    """
    executed = False
    cleanup = False

    @classmethod
    def setUpClass(cls):
        cls.executed = True

        def doCleanup():
            cls.cleanup = True
        cls.addClassCleanup(doCleanup)

    def test_dummy(self):
        pass


class Test02ClassCleanupsCheck(BaseCase):
    def test_classcleanups(self):
        self.assertTrue(Test01ClassCleanups.executed, "This test only makes sence when executed after Test01ClassCleanups")
        self.assertTrue(Test01ClassCleanups.cleanup, "TestClassCleanup shoudl have been cleanuped")


@skip
class TestSkipClass(BaseCase):
    def test_classcleanups(self):
        raise Exception('This should be skipped')


class TestSkipMethof(BaseCase):
    @skip
    def test_skip_method(self):
        raise Exception('This should be skipped')
