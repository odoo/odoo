__all__ = ['run_tests']

import logging
import re
import sys
from psycopg2.extensions import STATUS_READY

import odoo
from odoo.modules.registry import Registry

from .loader import make_suite, run_suite
from .result import OdooTestResult

_logger = logging.getLogger(__name__)

TEST_MODULE_NAME_PATTERN = re.compile(r'^odoo\.addons\.\w+\.tests')


def run_tests(env, test_tags, modules=None, reload_tests=False):
    """Run tests for the given modules and test tags."""

    if odoo.cli.COMMAND != 'shell':
        _logger.error('run_tests should be used only in odoo shell')
        return

    if odoo.tools.config['workers'] != 0:
        _logger.error('run_tests should be used only in threaded mode')
        return

    from odoo.service.server import server  # noqa: PLC0415
    if not server.httpd:
        # some tests need the http daemon to be available...
        server.http_spawn()

    if env.cr._cnx.status != STATUS_READY:
        # rollback the cr in case it holds a database lock which may cause deadlock while running tests
        _logger.warning("Rolling backin the transaction before testing")
        env.cr.rollback()

    if not modules:
        modules = sorted(env.registry._init_modules)

    if reload_tests:
        _clear_loaded_test_modules()

    odoo.tools.config['test_tags'] = test_tags
    odoo.tools.config['test_enable'] = True
    report = _run_tests(env.cr.dbname, modules)
    odoo.tools.config['test_enable'] = None
    odoo.tools.config['test_tags'] = None

    _log_test_report(report)

    return report


def _run_tests(db_name, modules):
    report = OdooTestResult()

    # Run at_install tests
    with Registry._lock:
        registry = Registry(db_name)
        try:
            # best effort to restore the test environment
            registry.loaded = False
            registry.ready = False
            at_install_suite = make_suite(modules, 'at_install')
            if at_install_suite.countTestCases():
                _logger.info("Starting at_install tests")
                report.update(run_suite(at_install_suite, report))
        finally:
            registry.loaded = True
            registry.ready = True

    # Run post_install tests
    post_install_suite = make_suite(modules, 'post_install')
    if post_install_suite.countTestCases():
        _logger.info("Starting post_install tests")
        report.update(run_suite(post_install_suite, report))

    return report


def _clear_loaded_test_modules():
    """Clear loaded test modules that may have been modified."""
    for module_key in list(sys.modules):
        if TEST_MODULE_NAME_PATTERN.match(module_key):
            _logger.debug("Removing module from sys.modules for reload: %s", module_key)
            del sys.modules[module_key]


def _log_test_report(report):
    if not report.wasSuccessful():
        _logger.error('Tests failed: %s', report)
    elif not report.testsRun:
        _logger.warning('No tests executed: %s', report)
    else:
        _logger.info('Tests passed: %s', report)
