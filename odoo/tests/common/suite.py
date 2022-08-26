import logging
import sys
import unittest.suite
import unittest.util

from ..runner import stats_logger

if sys.version_info >= (3, 8):
    BackportSuite = unittest.suite.TestSuite
else:
    class BackportSuite(unittest.suite.TestSuite):
        # Partial backport of bpo-24412, merged in CPython 3.8

        def _handleClassSetUp(self, test, result):
            previousClass = getattr(result, '_previousTestClass', None)
            currentClass = test.__class__
            if currentClass == previousClass:
                return
            if result._moduleSetUpFailed:
                return
            if getattr(currentClass, "__unittest_skip__", False):
                return

            try:
                currentClass._classSetupFailed = False
            except TypeError:
                # test may actually be a function
                # so its class will be a builtin-type
                pass

            setUpClass = getattr(currentClass, 'setUpClass', None)
            if setUpClass is not None:
                unittest.suite._call_if_exists(result, '_setupStdout')
                try:
                    setUpClass()
                except Exception as e:
                    if isinstance(result, unittest.suite._DebugResult):
                        raise
                    currentClass._classSetupFailed = True
                    className = unittest.util.strclass(currentClass)
                    self._createClassOrModuleLevelException(result, e,
                                                            'setUpClass',
                                                            className)
                finally:
                    unittest.suite._call_if_exists(result, '_restoreStdout')
                    if currentClass._classSetupFailed is True:
                        if hasattr(currentClass, 'doClassCleanups'):
                            currentClass.doClassCleanups()
                            if len(currentClass.tearDown_exceptions) > 0:
                                for exc in currentClass.tearDown_exceptions:
                                    self._createClassOrModuleLevelException(
                                            result, exc[1], 'setUpClass', className,
                                            info=exc)

        def _createClassOrModuleLevelException(self, result, exc, method_name, parent, info=None):
            errorName = f'{method_name} ({parent})'
            self._addClassOrModuleLevelException(result, exc, errorName, info)

        def _addClassOrModuleLevelException(self, result, exception, errorName, info=None):
            error = unittest.suite._ErrorHolder(errorName)
            addSkip = getattr(result, 'addSkip', None)
            if addSkip is not None and isinstance(exception, unittest.case.SkipTest):
                addSkip(error, str(exception))
            else:
                if not info:
                    result.addError(error, sys.exc_info())
                else:
                    result.addError(error, info)

        def _tearDownPreviousClass(self, test, result):
            previousClass = getattr(result, '_previousTestClass', None)
            currentClass = test.__class__
            if currentClass == previousClass:
                return
            if getattr(previousClass, '_classSetupFailed', False):
                return
            if getattr(result, '_moduleSetUpFailed', False):
                return
            if getattr(previousClass, "__unittest_skip__", False):
                return

            tearDownClass = getattr(previousClass, 'tearDownClass', None)
            if tearDownClass is not None:
                unittest.suite._call_if_exists(result, '_setupStdout')
                try:
                    tearDownClass()
                except Exception as e:
                    if isinstance(result, unittest.suite._DebugResult):
                        raise
                    className = unittest.util.strclass(previousClass)
                    self._createClassOrModuleLevelException(result, e,
                                                            'tearDownClass',
                                                            className)
                finally:
                    unittest.suite._call_if_exists(result, '_restoreStdout')
                    if hasattr(previousClass, 'doClassCleanups'):
                        previousClass.doClassCleanups()
                        if len(previousClass.tearDown_exceptions) > 0:
                            for exc in previousClass.tearDown_exceptions:
                                className = unittest.util.strclass(previousClass)
                                self._createClassOrModuleLevelException(result, exc[1],
                                                                        'tearDownClass',
                                                                        className,
                                                                        info=exc)

class OdooSuite(BackportSuite):
    def _handleClassSetUp(self, test, result):
        previous_test_class = getattr(result, '_previousTestClass', None)
        if not (
                previous_test_class != type(test)
            and hasattr(result, 'stats')
            and stats_logger.isEnabledFor(logging.INFO)
        ):
            super()._handleClassSetUp(test, result)
            return

        test_class = type(test)
        test_id = f'{test_class.__module__}.{test_class.__qualname__}.setUpClass'
        with result.collectStats(test_id):
            super()._handleClassSetUp(test, result)

    def _tearDownPreviousClass(self, test, result):
        previous_test_class = getattr(result, '_previousTestClass', None)
        if not (
                previous_test_class
            and previous_test_class != type(test)
            and hasattr(result, 'stats')
            and stats_logger.isEnabledFor(logging.INFO)
        ):
            super()._tearDownPreviousClass(test, result)
            return

        test_id = f'{previous_test_class.__module__}.{previous_test_class.__qualname__}.tearDownClass'
        with result.collectStats(test_id):
            super()._tearDownPreviousClass(test, result)
