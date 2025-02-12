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
from typing import Tuple, Any, Type, Dict
from collections import defaultdict

from . import case
from .common import HttpCase, get_db_name, TransactionCase
from .result import stats_logger
from unittest import util, BaseTestSuite, TestCase, mock
from odoo.api import Environment, SUPERUSER_ID
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
            assert isinstance(test, (TestCase))
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

# TODO: We actually want to use BaseCase not TransactionCase
PartialTestOrderKeyData = Tuple[Type[TransactionCase], Tuple[Any]]
"""A test class with its dependencies"""
TestOrderKeyData = Tuple[*PartialTestOrderKeyData, Type[TransactionCase]]
"""A test class with dependency and install class"""
"""A Class and its dependencies"""
TestOrderKey = Tuple[TestOrderKeyData, ...]
"""List of class and dependencies in order of application"""

class OdooSuite(TestSuite):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._order_key_cache: Dict[Type[TransactionCase], TestOrderKey] = {}
        self._stackenv = []

    def run(self, result, debug=False):
        self._reorder_tests()
        self.registry = Registry(get_db_name())
        with self.registry.cursor() as cr, \
            mock.patch.object(cr, 'close', lambda *_: None):
            self.cr = cr
            try:
                # As psql's NOW() returns the time when the transaction was started
                # some tests relying on time passed using that function might fail
                # if the test is ran after a certain time after the transaction is opened.
                # The following patches overrides psql's NOW method such that it returns
                # the timestamp at which the class's setUpClass was ran.
                cr.execute("CREATE SCHEMA IF NOT EXISTS __odoo_overrides")
                # pg_catalog must appear after our override schema.
                cr.execute('SET search_path TO "$user", public, __odoo_overrides, pg_catalog')
                res = super().run(result, debug=debug)
            finally:
                cr.transaction = None
                cr.rollback()
            return res

    def _get_test_order_key(self, cls) -> TestOrderKey:
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
        def _get_install_class(kls, depends, new_key: Tuple[PartialTestOrderKeyData]) -> Type[TransactionCase]:
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
        old_tests = self._tests
        self._tests = []

        nested_tests = {'tests': []}
        for test in old_tests:
            key = self._get_test_order_key(type(test))
            current_data = nested_tests
            for order in key:
                current_data = current_data.setdefault('subtests', defaultdict(lambda: {'tests': []}))[order]
            current_data['tests'].append(test)

        def _visit_node(node):
            if 'tests' in node:
                self._tests.extend(node['tests'])
            if 'subtests' in node:
                for v in node['subtests'].values():
                    _visit_node(v)
        _visit_node(nested_tests)

    def _clean_filestore(self, env=None):
        """
        Cleans the filestore using :code:`self.cr`, attachment can be created/unlinked
        during tests and this can add up and take quite some disc space.
        Crons are usually responsible for cleaning up but since they are not running during tests,
        we need to do it manually.

        This is called on class cleanup and on bundle cleanup
        """
        if not env:
            env = Environment(self.cr, SUPERUSER_ID, {})
        env['ir.attachment']._gc_file_store_unsafe()

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
        if previous_key == new_key and (not previous_class or not previous_class._commonDataFailed):
            return True
        idx = 0
        while idx < len(new_key) and idx < len(previous_key) and new_key[idx] == previous_key[idx]:
            idx += 1
        for p_idx in reversed(range(idx, len(previous_key))):
            if p_idx >= len(self._stackenv):
                continue
            order = previous_key[p_idx]
            _logger.debug('Uninstalling setUpCommonData from %s with class %s with dependencies %s', order[0], order[2], order[1])
            self.cr.execute('ROLLBACK TO SAVEPOINT "%s"', (f'common_data_{p_idx}', ))
            self._stackenv.pop()
        # if idx = 0, we have the opportunity to recreate `cr` here.
        for n_idx in range(idx, len(new_key)):
            order = new_key[n_idx]
            self.cr.execute('SAVEPOINT "%s"', (f'common_data_{n_idx}', ))
            kls = order[2]
            try:
                if kls == order[0]:
                    method = kls.setUpCommonData
                else:
                    k_idx = kls.__mro__.index(order[0])
                    if k_idx == 0:
                        method = kls.setUpCommonData
                    else:
                        method = super(kls.__mro__[k_idx - 1], kls).setUpCommonData
            except:
                breakpoint()
                raise
            kls.registry = self.registry
            kls.cr = self.cr
            kls.env = self._stackenv[-1]() if self._stackenv else Environment(self.cr, SUPERUSER_ID, {})
            if self.cr.transaction:
                self.cr.transaction.default_env = kls.env
            _logger.debug(
                'Installing setUpCommonData from %s with class %s with dependencies %s',
                order[0], kls, order[1]
            )
            try:
                method()
            except Exception as e:
                test_class._classSetupFailed = True
                test_class._commonDataFailed = True
                className = util.strclass(test_class)
                self._createClassOrModuleLevelException(
                    result, e,
                    'setUpCommonData',
                    className
                )
                self.cr.execute('ROLLBACK TO SAVEPOINT "%s"', (f'common_data_{n_idx}', ))
                return False
            kls.env.flush_all()
            lazy_property.reset_all(kls.env)
            self._stackenv.append(kls.env)
        return True

    def _handleClassSetUp(self, test, result):
        previous_test_class = result._previousTestClass
        test_class = type(test)
        is_new_class = previous_test_class != test_class
        with ExitStack() as stack:
            # Override NOW()
            test_class.registry = self.registry
            test_class.cr = self.cr
            if is_new_class:
                if not self._setup_common_data(previous_test_class, test_class, result):
                    return
                test_class.env = self._stackenv[-1]() if self._stackenv else Environment(self.cr, SUPERUSER_ID, {})
                if self.cr.transaction:
                    self.cr.transaction.default_env = test_class.env
                now = datetime.now(timezone.utc)
                self._cr = now
                self.cr.execute("SAVEPOINT savepoint_suite")
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
            if is_new_class:
                self.cr.clear()
                self.cr.cache = {}
                if self.cr.transaction:
                    self.cr.transaction.reset()
                self.cr.precommit.clear()
                self.cr.postcommit.clear()
                self.cr.prerollback.clear()
                self.cr.postrollback.clear()
                if not previous_test_class._commonDataFailed:
                    self.cr.execute('ROLLBACK TO SAVEPOINT savepoint_suite')
                self.cr._now = None
                # Also clean the filestore
                self._clean_filestore()
            return res

    def has_http_case(self):
        return self.countTestCases() and any(isinstance(test_case, HttpCase) for test_case in self)
