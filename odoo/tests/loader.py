import importlib
import importlib.util
import inspect
import logging
import sys
import threading
from pathlib import Path
from unittest import case

from .. import tools
from .tag_selector import TagsSelector
from .suite import OdooSuite
from .result import OdooTestResult


_logger = logging.getLogger(__name__)


def get_module_test_cases(module):
    """Return a suite of all test cases contained in the given module"""
    for obj in module.__dict__.values():
        if not isinstance(obj, type):
            continue
        if not issubclass(obj, case.TestCase):
            continue
        if obj.__module__ != module.__name__:
            continue

        test_case_class = obj
        test_cases = test_case_class.__dict__.items()
        if getattr(test_case_class, 'allow_inherited_tests_method', False):
            # keep iherited method for specific classes.
            # This is likely to be removed once a better solution is found
            test_cases = inspect.getmembers(test_case_class, callable)
        else:
            # sort test case to keep the initial behaviour.
            # This is likely to be removed in the future
            test_cases = sorted(test_cases, key=lambda pair: pair[0])

        for method_name, method in test_cases:
            if not callable(method):
                continue
            if not method_name.startswith('test'):
                continue
            yield test_case_class(method_name)


def get_test_modules(module):
    """ Return a list of module for the addons potentially containing tests to
    feed get_module_test_cases() """
    results = _get_tests_modules(importlib.util.find_spec(f'odoo.addons.{module}'))
    results += list(_get_upgrade_test_modules(module))

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


def _get_upgrade_test_modules(module):
    upgrade_modules = (
        f"odoo.upgrade.{module}",
        f"odoo.addons.{module}.migrations",
        f"odoo.addons.{module}.upgrades",
    )
    for module_name in upgrade_modules:
        if not importlib.util.find_spec(module_name):
            continue

        upg = importlib.import_module(module_name)
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
        for t in get_module_test_cases(m)
        if position_tag.check(t) and config_tags.check(t)
    )
    return OdooSuite(sorted(tests, key=lambda t: t.test_sequence))


def run_suite(suite, global_report=None):
    # avoid dependency hell
    from ..modules import module
    module.current_test = True
    threading.current_thread().testing = True

    results = OdooTestResult(global_report=global_report)
    suite(results)

    threading.current_thread().testing = False
    module.current_test = False
    return results
