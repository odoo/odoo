import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest import TestCase as _StdTestCase

from .. import tools
from ..libs.debug_log import DebugLog
from . import common
from .result import OdooTestResult
from .suite import OdooSuite
from .tag_selector import TagsSelector

_debug = DebugLog(__name__)

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator


def get_module_test_cases(module: Any) -> Iterator[_StdTestCase]:
    for obj in module.__dict__.values():
        if not isinstance(obj, type):
            continue
        if not issubclass(obj, _StdTestCase):
            continue
        if obj.__module__ != module.__name__:
            continue

        test_case_class = obj
        inherited = bool(
            getattr(test_case_class, "allow_inherited_tests_method", False)
        )
        if inherited:
            test_cases = inspect.getmembers(test_case_class, callable)
        else:
            test_cases = sorted(test_case_class.__dict__.items())

        yielded = 0  # debuglog
        for method_name, method in test_cases:
            if not callable(method):
                continue
            if not method_name.startswith("test"):
                continue
            yielded += 1  # debuglog
            yield test_case_class(method_name)
        _debug.perf.count(
            "test.loader.cases_collected",
            cls=test_case_class.__qualname__,
            inherited=inherited,
            cases=yielded,
        )


def get_test_modules(module: str) -> list[Any]:
    with _debug.perf("test.loader.import_tests", module=module) as span:
        results = _get_tests_modules(f"odoo.addons.{module}")
        upgrade = list(_get_upgrade_test_modules(module))  # debuglog
        results += upgrade
        span.set(modules=len(results), upgrade=len(upgrade))

    return results


def _get_tests_modules(package_name: str) -> list[Any]:
    spec = importlib.util.find_spec(".tests", package_name)
    if not spec:
        _debug.logic("test.loader.no_tests_package", package=package_name)
        return []

    tests_mod = importlib.import_module(spec.name)
    return [
        mod_obj
        for name, mod_obj in inspect.getmembers(tests_mod, inspect.ismodule)
        if name.startswith("test_")
    ]


def _get_upgrade_test_modules(module: str) -> Generator[Any]:
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
                spec = importlib.util.spec_from_file_location(
                    f"{upg.__name__}.tests.{test.stem}", test
                )
                if not spec:
                    continue
                if (pymod := sys.modules.get(spec.name)) is None:
                    pymod = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = pymod
                    assert spec.loader is not None
                    try:
                        spec.loader.exec_module(pymod)
                    except BaseException as exc:
                        _debug.lifecycle(
                            "test.loader.upgrade_test_failed",
                            module=spec.name,
                            error=type(exc).__name__,
                        )
                        sys.modules.pop(spec.name, None)
                        raise
                    _debug.lifecycle(
                        "test.loader.upgrade_test_loaded", module=spec.name
                    )
                else:
                    _debug.logic("test.loader.upgrade_test_cached", module=spec.name)
                yield pymod


def prepare_suite(module_names: list[str], position: str = "at_install") -> OdooSuite:
    config_tags = TagsSelector(tools.config["test_tags"])
    position_tag = TagsSelector(position)
    tests = []
    with _debug.perf(
        "test.suite.collect", position=position, modules=len(module_names)
    ) as span:
        for module_name in module_names:
            collected = selected = 0  # debuglog
            for m in get_test_modules(module_name):
                for t in get_module_test_cases(m):
                    collected += 1  # debuglog
                    if position_tag.selects(t) and config_tags.select_test(t):
                        selected += 1  # debuglog
                        tests.append(t)
            _debug.logic(
                "test.suite.module_selected",
                module=module_name,
                position=position,
                collected=collected,
                selected=selected,
            )
        span.set(tests=len(tests))
    _debug.pipeline(
        "test.suite.prepared",
        modules=len(module_names),
        position=position,
        tests=len(tests),
        tags=tools.config["test_tags"] or None,
    )
    return OdooSuite(sorted(tests, key=lambda t: getattr(t, "test_sequence", 0)))


def run_suite(
    suite: OdooSuite, global_report: OdooTestResult | None = None
) -> OdooTestResult:
    from ..modules import module

    module.current_test = True
    if _debug.lifecycle.enabled:
        _debug.lifecycle(
            "test.suite.start",
            tests=suite.countTestCases(),
            http=suite.has_http_case(),
            global_report=global_report is not None,
        )
    try:
        results = OdooTestResult(global_report=global_report)
        with _debug.perf("test.suite.run", tests=suite.countTestCases()) as span:
            suite.run(results)
            span.set(
                ran=results.testsRun,
                failures=results.failures_count,
                errors=results.errors_count,
                skipped=results.skipped,
                halted=results.shouldStop,
            )
    finally:
        module.current_test = False
        common.gc_test_filestore()
    return results
