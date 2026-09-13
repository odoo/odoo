__all__ = ["run_tests"]

import logging
import re
import sys
from typing import Any

from psycopg.pq import TransactionStatus

import odoo
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry

from .loader import prepare_suite, run_suite
from .result import OdooTestResult

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

TEST_MODULE_NAME_PATTERN = re.compile(
    r"^odoo\.(?:addons\.\w+\.(?:migrations\.|upgrades\.)?tests|upgrade\.\w+\.tests)"
)


def run_tests(
    env: Any,
    test_tags: str,
    modules: list[str] | None = None,
    reload_tests: bool = False,
) -> OdooTestResult | None:

    if odoo.cli.COMMAND != "shell":
        _debug.logic("test.shell.refused", reason="not_shell", command=odoo.cli.COMMAND)
        _logger.error("run_tests should be used only in odoo shell")
        return None

    if odoo.tools.config["workers"] != 0:
        _debug.logic(
            "test.shell.refused",
            reason="workers",
            workers=odoo.tools.config["workers"],
        )
        _logger.error("run_tests should be used only in threaded mode")
        return None

    from odoo.service.server import ThreadedServer, get_server

    server = get_server()
    if not isinstance(server, ThreadedServer):
        _debug.logic(
            "test.shell.refused",
            reason="no_threaded_server",
            server=type(server).__name__,
        )
        _logger.error("run_tests needs a threaded server; none is running")
        return None

    if not server.httpd:
        server.spawn_http_server()
        _debug.lifecycle("test.shell.http_spawned")

    if env.cr.connection.info.transaction_status != TransactionStatus.IDLE:
        _debug.logic(
            "test.shell.rollback_before",
            status=env.cr.connection.info.transaction_status.name,
        )
        _logger.warning("Rolling back the transaction before testing")
        env.cr.rollback()

    if not modules:
        modules = sorted(env.registry.loaded_modules)

    if reload_tests:
        _clear_loaded_test_modules()

    _debug.pipeline(
        "test.shell.run",
        db=env.cr.dbname,
        modules=len(modules),
        tags=test_tags,
        reload=reload_tests,
    )
    old_test_tags = odoo.tools.config["test_tags"]
    old_test_enable = odoo.tools.config["test_enable"]
    odoo.tools.config["test_tags"] = test_tags
    odoo.tools.config["test_enable"] = True
    try:
        report = _run_tests(env.cr.dbname, modules)
    finally:
        odoo.tools.config["test_enable"] = old_test_enable
        odoo.tools.config["test_tags"] = old_test_tags

    _log_test_report(report)

    return report


def _run_tests(db_name: str, modules: list[str]) -> OdooTestResult:
    report = OdooTestResult()

    with Registry._lock:
        registry = Registry(db_name)
        try:
            registry.loaded = False
            registry.ready = False
            at_install_suite = prepare_suite(modules, "at_install")
            _debug.pipeline(
                "test.shell.position",
                position="at_install",
                tests=at_install_suite.countTestCases(),
            )
            if at_install_suite.countTestCases():
                _logger.info("Starting at_install tests")
                with _debug.perf("test.shell.position_run", position="at_install"):
                    report.update(run_suite(at_install_suite, report))
        finally:
            registry.loaded = True
            registry.ready = True

    post_install_suite = prepare_suite(modules, "post_install")
    _debug.pipeline(
        "test.shell.position",
        position="post_install",
        tests=post_install_suite.countTestCases(),
    )
    if post_install_suite.countTestCases():
        _logger.info("Starting post_install tests")
        with _debug.perf("test.shell.position_run", position="post_install"):
            report.update(run_suite(post_install_suite, report))

    return report


def _clear_loaded_test_modules() -> None:
    removed = 0  # debuglog
    for module_key in list(sys.modules):
        if TEST_MODULE_NAME_PATTERN.match(module_key):
            _logger.debug("Removing module from sys.modules for reload: %s", module_key)
            del sys.modules[module_key]
            removed += 1  # debuglog
    _debug.lifecycle("test.shell.modules_reloaded", removed=removed)


def _log_test_report(report: OdooTestResult) -> None:
    if not report.wasSuccessful():
        _logger.error("Tests failed: %s", report)
    elif not report.testsRun:
        _logger.warning("No tests executed: %s", report)
    else:
        _logger.info("Tests passed: %s", report)
