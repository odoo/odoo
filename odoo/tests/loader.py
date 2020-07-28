import importlib
import inspect
import itertools
import logging
import threading
import time
import unittest

import odoo
from .. import tools
from .common import TagsSelector, OdooSuite
from .runner import OdooTestRunner, OdooTestResult

# backwards compatibility
_logger = logging.getLogger('odoo.modules.module')

def get_test_modules(module):
    """ Return a list of module for the addons potentially containing tests to
    feed unittest.TestLoader.loadTestsFromModule() """
    # Try to import the module
    results = _get_tests_modules('odoo.addons', module)

    try:
        importlib.import_module('odoo.upgrade.%s' % module)
    except ImportError:
        pass
    else:
        results += _get_tests_modules('odoo.upgrade', module)

    return results


def _get_tests_modules(path, module):
    modpath = '%s.%s' % (path, module)
    try:
        mod = importlib.import_module('.tests', modpath)
    except ImportError as e:  # will also catch subclass ModuleNotFoundError of P3.6
        # Hide ImportErrors on `tests` sub-module, but display other exceptions
        if e.name == modpath + '.tests' and e.msg.startswith('No module named'):
            return []
        _logger.exception('Can not `import %s`.', module)
        return []
    except Exception as e:
        _logger.exception('Can not `import %s`.', module)
        return []
    if hasattr(mod, 'fast_suite') or hasattr(mod, 'checks'):
        _logger.warning(
            "Found deprecated fast_suite or checks attribute in test module "
            "%s. These have no effect in or after version 8.0.",
            mod.__name__)

    result = [mod_obj for name, mod_obj in inspect.getmembers(mod, inspect.ismodule)
              if name.startswith('test_')]
    return result


def run_unit_tests(module_name, position='at_install'):
    """
    :returns: ``True`` if all of ``module_name``'s tests succeeded, ``False``
              if any of them failed, ``None`` if no tests were ran.
    :rtype: bool | None
    """
    from ..modules import module
    # avoid dependency hell
    module.current_test = module_name
    mods = get_test_modules(module_name)
    threading.currentThread().testing = True
    config_tags = TagsSelector(tools.config['test_tags'])
    position_tag = TagsSelector(position)

    results = OdooTestResult()
    for m in mods:
        tests = unwrap_suite(unittest.TestLoader().loadTestsFromModule(m))
        suite = OdooSuite(t for t in tests if position_tag.check(t) and config_tags.check(t))

        if suite.countTestCases():
            t0 = time.time()
            t0_sql = odoo.sql_db.sql_counter
            _logger.info('%s running tests.', m.__name__)
            result = OdooTestRunner().run(suite)
            results.update(result)
            log_level = logging.INFO
            if time.time() - t0 > 5:
                log_level = logging.RUNBOT
            _logger.log(log_level, "%s ran %s tests in %.2fs, %s queries", m.__name__, result.testsRun, time.time() - t0, odoo.sql_db.sql_counter - t0_sql)
            if not result.wasSuccessful():
                _logger.error("Module %s: %d failures, %d errors", module_name, len(result.failures), len(result.errors))

    module.current_test = None
    threading.currentThread().testing = False

    return results


def unwrap_suite(test):
    """
    Attempts to unpack testsuites (holding suites or cases) in order to
    generate a single stream of terminals (either test cases or customized
    test suites). These can then be checked for run/skip attributes
    individually.

    An alternative would be to use a variant of @unittest.skipIf with a state
    flag of some sort e.g. @unittest.skipIf(common.runstate != 'at_install'),
    but then things become weird with post_install as tests should *not* run
    by default there
    """
    if isinstance(test, unittest.TestCase):
        yield test
        return

    subtests = list(test)
    # custom test suite (no test cases)
    if not len(subtests):
        yield test
        return

    for item in itertools.chain.from_iterable(unwrap_suite(t) for t in subtests):
        yield item
