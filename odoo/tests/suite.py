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

from . import case
from .common import HttpCase, get_db_name
from .result import stats_logger
from unittest import util, BaseTestSuite, TestCase, mock
from odoo.modules.registry import Registry

__unittest = True


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


class OdooSuite(TestSuite):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, result, debug=False):
        self.registry = Registry(get_db_name())
        with self.registry.cursor() as cr, \
            mock.patch.object(cr, 'close', lambda *_: _):
            self.cr = cr
            # As psql's NOW() returns the time when the transaction was started
            # some tests relying on time passed using that function might fail
            # if the test is ran after a certain time after the transaction is opened.
            # The following patches overrides psql's NOW method such that it returns
            # the timestamp at which the class's setUpClass was ran.
            cr.execute("CREATE SCHEMA IF NOT EXISTS __odoo_overrides")
            # pg_catalog must appear after our override schema.
            cr.execute('SET search_path TO "$user", public, __odoo_overrides, pg_catalog')
            return super().run(result, debug=debug)

    def _handleClassSetUp(self, test, result):
        previous_test_class = result._previousTestClass
        test_class = type(test)
        is_new_class = previous_test_class != test_class
        with ExitStack() as stack:
            # Override NOW()
            if is_new_class:
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
            if is_new_class and hasattr(result, 'stat') and stats_logger.isEnabledFor(logging.INFO):
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
                self.cr.transaction = None
                self.cr.precommit.clear()
                self.cr.postcommit.clear()
                self.cr.prerollback.clear()
                self.cr.postrollback.clear()
                self.cr.execute('ROLLBACK TO SAVEPOINT savepoint_suite')
                self.cr._now = None
            return res

    def has_http_case(self):
        return self.countTestCases() and any(isinstance(test_case, HttpCase) for test_case in self)
