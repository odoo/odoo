import importlib
import importlib.util
import inspect
import itertools
import threading
import unittest

from .. import tools
from .tag_selector import TagsSelector
from .suite import OdooSuite
from .result import OdooTestResult


def get_test_modules(module):
    """ Return a list of module for the addons potentially containing tests to
    feed unittest.TestLoader.loadTestsFromModule() """
    results = _get_tests_modules(importlib.util.find_spec(f'odoo.addons.{module}'))

    upgrade_spec = importlib.util.find_spec(f'odoo.upgrade.{module}')
    if upgrade_spec:
        results += _get_tests_modules(upgrade_spec)

    return results


def _get_tests_modules(mod):
    spec = importlib.util.find_spec('.tests', mod.name)
    if not spec:
        return []

    tests_mod = importlib.import_module(spec.name)
    return [
        mod_obj
        for name, mod_obj in inspect.getmembers(tests_mod, inspect.ismodule)
        if name.startswith('test_')
    ]


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
    ## custom test suite (no test cases)
    #if not len(subtests):
    #    yield test
    #    return

    for item in itertools.chain.from_iterable(unwrap_suite(t) for t in subtests):
        yield item
