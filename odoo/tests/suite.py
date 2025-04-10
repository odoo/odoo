"""
Vendor unittest.TestSuite

This is a modified version of python 3.8 unitest.TestSuite

Odoo tests customisation combined with the need of a cross version compatibility
started to make TestSuite and other unitest object more complicated than vendoring
the part we need for Odoo. This versions is simplified in order
to minimise the code to maintain

- Removes expected failure support
- Removes module setUp/tearDown support

"""

import logging
import sys
from datetime import datetime, timezone
from contextlib import ExitStack
import itertools
from typing import Tuple, Any, Type, Dict, List
from collections import defaultdict

import odoo
from . import case
from .common import HttpCase, get_db_name, TransactionCase, BaseCase, RegistrySavepoint
from .result import stats_logger
from unittest import util, BaseTestSuite, TestCase, mock
from odoo.api import Environment, SUPERUSER_ID
from odoo.sql_db import Savepoint, BaseCursor
from odoo.tools import lazy_property
from odoo.modules.registry import Registry

__unittest = True
_logger = logging.getLogger(__name__)

class TestSuite(BaseTestSuite):
    """A test suite is a composite test consisting of a number of TestCases.
    For use, create an instance of TestSuite, then add test case instances.
    When all tests have been added, the suite can be passed to a test
    runner, such as TextTestRunner. It will run the individual test cases
    in the order in which they were added, aggregating the results. When
    subclassing, do not forget to call the base class constructor.
    """

    def run(self, result, debug=False):
        for test in self:
            if result.shouldStop:
                break
            assert isinstance(test, (TestCase))
            odoo.modules.module.current_test = test
            self._tearDownPreviousClass(test, result)
            self._handleClassSetUp(test, result)
            result._previousTestClass = test.__class__

            if not test.__class__._classSetupFailed:
                test(result)

        self._tearDownPreviousClass(None, result)
        return result

    def _handleClassSetUp(self, test, result):
        previousClass = result._previousTestClass
        currentClass = test.__class__
        if currentClass == previousClass:
            return
        if result._moduleSetUpFailed:
            return
        if currentClass.__unittest_skip__:
            return

        currentClass._classSetupFailed = False

        try:
            currentClass.setUpClass()
        except Exception as e:
            currentClass._classSetupFailed = True
            className = util.strclass(currentClass)
            self._createClassOrModuleLevelException(result, e,
                                                    'setUpClass',
                                                    className)
        finally:
            if currentClass._classSetupFailed is True:
                currentClass.doClassCleanups()
                if len(currentClass.tearDown_exceptions) > 0:
                    for exc in currentClass.tearDown_exceptions:
                        self._createClassOrModuleLevelException(
                                result, exc[1], 'setUpClass', className,
                                info=exc)

    def _createClassOrModuleLevelException(self, result, exception, method_name,
                                           parent, info=None):
        errorName = f'{method_name} ({parent})'
        error = _ErrorHolder(errorName)
        if isinstance(exception, case.SkipTest):
            result.addSkip(error, str(exception))
        else:
            if not info:
                result.addError(error, sys.exc_info())
            else:
                result.addError(error, info)

    def _tearDownPreviousClass(self, test, result):
        previousClass = result._previousTestClass
        currentClass = test.__class__
        if currentClass == previousClass:
            return
        if not previousClass:
            return
        if previousClass._classSetupFailed:
            return
        if previousClass.__unittest_skip__:
            return
        try:
            previousClass.tearDownClass()
        except Exception as e:
            className = util.strclass(previousClass)
            self._createClassOrModuleLevelException(result, e,
                                                    'tearDownClass',
                                                    className)
        finally:
            previousClass.doClassCleanups()
            if len(previousClass.tearDown_exceptions) > 0:
                for exc in previousClass.tearDown_exceptions:
                    className = util.strclass(previousClass)
                    self._createClassOrModuleLevelException(result, exc[1],
                                                            'tearDownClass',
                                                            className,
                                                            info=exc)


class _ErrorHolder(object):
    """
    Placeholder for a TestCase inside a result. As far as a TestResult
    is concerned, this looks exactly like a unit test. Used to insert
    arbitrary errors into a test suite run.
    """
    # Inspired by the ErrorHolder from Twisted:
    # http://twistedmatrix.com/trac/browser/trunk/twisted/trial/runner.py

    # attribute used by TestResult._exc_info_to_string
    failureException = None

    def __init__(self, description):
        self.description = description

    def id(self):
        return self.description

    def shortDescription(self):
        return None

    def __repr__(self):
        return "<ErrorHolder description=%r>" % (self.description,)

    def __str__(self):
        return self.id()

    def run(self, result):
        # could call result.addError(...) - but this test-like object
        # shouldn't be run anyway
        pass

    def __call__(self, result):
        return self.run(result)

    def countTestCases(self):
        return 0

PartialTestOrderKeyData = Tuple[Type[TransactionCase], Tuple[Any]]
"""A test class with its dependencies"""
TestOrderKeyData = Tuple[Type[TransactionCase], Tuple[Any], Type[TransactionCase]]
"""A test class with dependency and install class"""
TestOrderKey = Tuple[TestOrderKeyData, ...]
"""List of class and dependencies in order of application"""

class OdooSuite(TestSuite):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._order_key_cache: Dict[Type[BaseCase], TestOrderKey] = {}
        self._stackenv: List[Environment] = []
        self._savepoints: List[Savepoint] = []
        self._registry_savepoints: List[RegistrySavepoint] = []

    def run(self, result, debug=False):
        self._reorder_tests()
        self.registry = Registry(get_db_name())
        self.cr: BaseCursor | None = None
        try:
            res = super().run(result, debug=debug)
        finally:
            if self.cr:
                self._close_cursor(unwind_savepoints=True)
        return res

    def _close_cursor(self, unwind_savepoints=False):
        """
        Closes the current cursor.

        If check_savepoints is True, the method raises an exception if a savepoint hasn't been closed.
        """
        assert hasattr(self.cr, '_patch'), 'cursor should have a patch object'
        if unwind_savepoints:
            while self._savepoints:
                self._pop_savepoint()
        assert len(self._savepoints) == 0, 'cursor was closed without cleaning savepoints'
        _logger.debug('Closing cursor')
        self.cr._patch.__exit__(None, None, None)
        self.cr.transaction = None
        self.cr.rollback()
        self.cr.close()
        self.cr = None

    def _open_cursor(self):
        """
        Returns a new cursor, if a cursor was already opened within the test suite,
        that cursor is closed and a new one is opened.
        """
        if self.cr:
            self._close_cursor()
        _logger.debug('Opening cursor')
        self.cr = self.registry.cursor()
        # Due to some tests relying on psql's `NOW()` function, and the time passed
        # between that function's return value and python's now(), we need to be able
        # to patch that method.
        # Using a schema and search_path we can override that function similarly to a
        # patcher.
        self.cr.execute("CREATE SCHEMA IF NOT EXISTS __odoo_overrides")
        # pg_catalog must appear after our override schema.
        self.cr.execute('SET search_path TO "$user", public, __odoo_overrides, pg_catalog')
        # `close` will be called by tearDownClass, however if we provided the cursor
        # this can safely be ignored.
        self.cr._patch = mock.patch.object(self.cr, 'close', lambda *_: None)
        self.cr._patch.__enter__() # Using __enter__ directly bypasses the patcher check in BaseCase
        return self.cr

    def _freeze_cursor(self):
        """
        Patches psql's :code:`NOW()` function with the current time (UTC).
        """
        assert self.cr
        now = datetime.now(timezone.utc)
        self.cr._now = None
        self.cr._now = now.replace(tzinfo=None)
        self.cr.execute("""
            CREATE OR REPLACE FUNCTION __odoo_overrides.now()
            RETURNS TIMESTAMPTZ
            AS
            $$
                BEGIN
                RETURN %s::TIMESTAMPTZ;
                END;
            $$
            LANGUAGE plpgsql STABLE PARALLEL SAFE STRICT;
        """, (now, ))

    def _push_savepoint(self):
        """
        Pushes a new savepoint on the current transaction.

        If no cursor is opened, opens a cursor.
        """
        if not self.cr:
            self._open_cursor()
        self._savepoints.append(Savepoint(self.cr))
        self._registry_savepoints.append(RegistrySavepoint(self.registry))

    def _pop_savepoint(self):
        """
        Pops the latest savepoint from the transaction.

        The filestore is cleaned every time we swap savepoints.
        """
        assert self.cr, 'Tried popping a savepoint without a cursor'
        assert self._savepoints, 'No savepoint to pop'
        savepoint = self._savepoints.pop()
        savepoint.close(rollback=True)
        self._registry_savepoints.pop().reset(self.cr)
        # We can only clean the filestore one all savepoints have been
        # removed, as they could otherwise delete files which would rollback.
        if not self._savepoints:
            self._clean_filestore()

    def _clean_filestore(self):
        """
        Cleans the filestore using :code:`self.cr`, attachment can be created/unlinked
        during tests and this can add up and take quite some disc space.
        Crons are usually responsible for cleaning up but since they are not running during tests,
        we need to do it manually.
        """
        env = Environment(self.cr, SUPERUSER_ID, {})
        env['ir.attachment']._gc_file_store_unsafe()

    def _get_test_order_key(self, cls: Type[BaseCase]) -> TestOrderKey:
        """
        Returns an order key for the given class.

        This is used both to reorganize the tests and to define which :code:`setUpCommonData` need to be called.
        """
        # Get call order from mro without TransactionCase (we never call TransactionCase.setUpCommonData)
        if cls in self._order_key_cache:
            return self._order_key_cache[cls]
        _mro = [
            kls for kls in cls.__mro__
            if issubclass(kls, TransactionCase)
            and kls != TransactionCase
            and 'setUpCommonData' in kls.__dict__
        ]

        previous_install_kls = None
        def _get_install_class(kls, depends, new_key: Tuple[PartialTestOrderKeyData, ...]) -> Type[TransactionCase]:
            nonlocal previous_install_kls
            # We need to call setUpCommonData from the closest class which changes the dependencies.
            # The class must be a subclass of the common class and a subclass of the previously installed
            # class, in case of multiple inheritance.
            kls_to_check = [
                kkls for kkls in cls.__mro__
                if issubclass(kkls, kls) and (
                    not previous_install_kls or issubclass(kkls, previous_install_kls)
                )
            ]
            install_kls = kls_to_check.pop(0)
            while kls_to_check:
                kls_key = self._get_test_order_key(kls_to_check[0])
                # kls_key without install class
                kls_key = tuple(o[:2] for o in kls_key)
                if new_key[:len(kls_key)] != kls_key:
                    break
                install_kls = kls_to_check.pop(0)
            previous_install_kls = install_kls
            return (kls, depends, install_kls)

        def _get_attrs(kls) -> PartialTestOrderKeyData:
            method = kls.__dict__['setUpCommonData']
            def _get_attr(attr):
                return tuple(
                    kls.__dict__[attr] for kls in cls.__mro__ if attr in kls.__dict__
                )
            if hasattr(method, '_data_depends'):
                return (kls, tuple(itertools.chain(*(_get_attr(attr) for attr in method._data_depends))))
            return (kls, tuple())

        # If the test does not inherit from TransactionCase, the following is empty.
        k = tuple(_get_attrs(kls) for kls in reversed(_mro))
        k = tuple(_get_install_class(kls, depends, k) for kls, depends in k)
        self._order_key_cache[cls] = k
        return k

    def _reorder_tests(self):
        """
        Re-order tests by `setUpCommonData` call order.

        Tests are ordered according to the setUpCommonData call stack and their
        defined dependencies.
        """
        nested_tests = {'tests': []}
        requires_sorting = False
        for test in self._tests:
            test_class = type(test)
            requires_sorting = requires_sorting or hasattr(test_class, 'test_sequence')
            key = self._get_test_order_key(test_class)
            current_data = nested_tests
            level = 0
            for order in key:
                current_data = current_data.setdefault('subtests', defaultdict(lambda: {'tests': []}))[order]
                level += 1
            assert level == 0 or issubclass(test_class, TransactionCase), \
                'Only transaction cases are allowed on sub-levels.'
            current_data['tests'].append(test)

        # Recursively visit nodes, tests are pushed on `self._tests` in order.
        self._tests = []
        def _visit_node(node):
            if 'tests' in node:
                self._tests.extend(node['tests'])
            if 'subtests' in node:
                for v in node['subtests'].values():
                    _visit_node(v)
        _visit_node(nested_tests)
        # While we do reorder tests, test_sequence has to be respected.
        if requires_sorting:
            self._tests.sort(key=lambda t: getattr(t, 'test_sequence', 0))

    def _setup_common_data(self, previous_class, test_class, result):
        """
        Prepares common data for the given class, data from previous_class is uninstalled in reverse order
        in order to keep common data that is common between the two classes.

        Returns False if something went wrong, True otherwise.
        """
        test_class._commonDataFailed = False
        _logger.debug('Prepping %s', test_class.__name__)
        previous_key = self._get_test_order_key(previous_class) if previous_class else tuple()
        new_key = self._get_test_order_key(test_class)
        if previous_key == new_key and (not previous_class or not getattr(previous_class, '_commonDataFailed', False)):
            return
        idx = 0
        while idx < len(new_key) and idx < len(previous_key) and new_key[idx] == previous_key[idx]:
            idx += 1
        for p_idx in reversed(range(idx, len(previous_key))):
            if p_idx >= len(self._stackenv):
                continue
            order = previous_key[p_idx]
            _logger.debug('Uninstalling setUpCommonData from %s with class %s with dependencies %s', order[0], order[2], order[1])
            self._pop_savepoint()
            self._stackenv.pop()
        if idx == 0 and self.cr:
            self._close_cursor()
        for n_idx in range(idx, len(new_key)):
            order = new_key[n_idx]
            self._push_savepoint()
            _logger.debug(
                'Installing setUpCommonData from %s with class %s with dependencies %s',
                order[0], order[2], order[1]
            )
            try:
                kls = order[2]
                if kls == order[0]:
                    method = kls.setUpCommonData
                else:
                    k_idx = kls.__mro__.index(order[0])
                    if k_idx == 0:
                        method = kls.setUpCommonData
                    else:
                        method = super(kls.__mro__[k_idx - 1], kls).setUpCommonData
                kls.registry = self.registry
                kls.cr = self.cr
                kls.env = self._stackenv[-1]() if self._stackenv else Environment(self.cr, SUPERUSER_ID, {})
                if self.cr.transaction:
                    self.cr.transaction.default_env = kls.env
                method()
                kls.env.flush_all()
                lazy_property.reset_all(kls.env)
                self._stackenv.append(kls.env)
            except Exception as e:
                test_class._classSetupFailed = True
                test_class._commonDataFailed = True
                className = util.strclass(test_class)
                self._createClassOrModuleLevelException(
                    result, e,
                    'setUpCommonData',
                    className
                )
                self._pop_savepoint()

    def _handleClassSetUp(self, test, result):
        previous_test_class = result._previousTestClass
        test_class = type(test)
        is_new_class = previous_test_class != test_class
        with ExitStack() as stack:
            if is_new_class and issubclass(test_class, TransactionCase):
                self._setup_common_data(previous_test_class, test_class, result)
                if test_class._commonDataFailed:
                    return
                # If we have a cursor, we have common data, in which case
                # we provide registry, cr and env attributes to the class and start
                # a new savepoint.
                if self.cr:
                    test_class.registry = self.registry
                    test_class.cr = self.cr
                    test_class.env = self._stackenv[-1]() if self._stackenv else Environment(self.cr, SUPERUSER_ID, {})
                    if self.cr.transaction:
                        self.cr.transaction.default_env = test_class.env
                    self._push_savepoint()
                    self._freeze_cursor()
                else:
                    # Because those attributes might be set on common classes
                    # and the test relies on those being set to determine
                    # whether or not they are independent, we need to clean them
                    # if we are not using common data.
                    test_class.registry = None
                    test_class.cr = None
                    test_class.env = None

            # Enable stat collection
            if is_new_class and hasattr(result, 'stats') and stats_logger.isEnabledFor(logging.INFO):
                test_id = f'{test_class.__module__}.{test_class.__qualname__}.setUpClass'
                stack.enter_context(result.collectStats(test_id))
            return super()._handleClassSetUp(test, result)

    def _tearDownPreviousClass(self, test, result):
        previous_test_class = result._previousTestClass
        test_class = type(test)
        is_new_class = previous_test_class and previous_test_class != test_class
        with ExitStack() as stack:
            # Enable stat collection
            if is_new_class and hasattr(result, 'stats') and stats_logger.isEnabledFor(logging.INFO):
                test_id = f'{previous_test_class.__module__}.{previous_test_class.__qualname__}.tearDownClass'
                stack.enter_context(result.collectStats(test_id))
            res = super()._tearDownPreviousClass(test, result)
            # Cleanup self.cr between tests
            # The registry itself is cleaned up by TransactionCase
            if is_new_class and self.cr:
                self.cr.clear()
                self.cr.cache = {}
                if self.cr.transaction:
                    self.cr.transaction.reset()
                self.cr.precommit.clear()
                self.cr.postcommit.clear()
                self.cr.prerollback.clear()
                self.cr.postrollback.clear()
                if not previous_test_class._commonDataFailed:
                    self._pop_savepoint()
            return res

    def has_http_case(self):
        return self.countTestCases() and any(isinstance(test_case, HttpCase) for test_case in self)
