import importlib
import inspect
import itertools
import logging
import sys
import threading
import unittest
from pathlib import Path

from .. import tools
from .common import TagsSelector, OdooSuite
from .runner import OdooTestResult


_logger = logging.getLogger(__name__)
def get_test_modules(module):
    """ Return a list of module for the addons potentially containing tests to
    feed unittest.TestLoader.loadTestsFromModule() """
    # Try to import the module
    results = _get_tests_modules('odoo.addons', module)
    results += list(_get_upgrade_test_modules(module))

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

def _get_upgrade_test_modules(module):
    upgrade_modules = (
        f"odoo.upgrade.{module}",
        f"odoo.addons.{module}.migrations",
        f"odoo.addons.{module}.upgrades",
    )
    for module_name in upgrade_modules:
        try:
            upg = importlib.import_module(module_name)
        except ImportError:
            continue

        for path in map(Path, upg.__path__):
            for test in path.glob("tests/test_*.py"):
                spec = importlib.util.spec_from_file_location(f"{upg.__name__}.tests.{test.stem}", test)
                if not spec:
                    continue
                pymod = importlib.util.module_from_spec(spec)
                sys.modules[spec.name] = pymod
                spec.loader.exec_module(pymod)
                yield pymod


def make_suite(module_names, position='at_install'):
    """ Creates a test suite for all the tests in the specified modules,
    filtered by the provided ``position`` and the current test tags

    :param list[str] module_names: modules to load tests from
    :param str position: "at_install" or "post_install"
    """
    config_tags = TagsSelector(tools.config['test_tags'])
    position_tag = TagsSelector(position)
    tests = (
        t
        for module_name in module_names
        for m in get_test_modules(module_name)
        for t in unwrap_suite(unittest.TestLoader().loadTestsFromModule(m))
        if position_tag.check(t) and config_tags.check(t)
    )
    return OdooSuite(sorted(tests, key=lambda t: t.test_sequence))

def run_suite(suite, module_name=None):
    # avoid dependency hell
    from ..modules import module
    module.current_test = module_name
    threading.current_thread().testing = True

    results = OdooTestResult()
    suite(results)

    threading.current_thread().testing = False
    module.current_test = None
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
