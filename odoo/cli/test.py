import argparse
import inspect
import logging
import textwrap
import threading
import time
from collections import Counter

import odoo
import odoo.http
import odoo.service.server as odoo_service
from odoo import SUPERUSER_ID
from odoo.api import Environment
from odoo.cli.command import Command
from odoo.modules.registry import Registry
from odoo.tools import config

_logger = logging.getLogger(__name__)


class Test(Command):
    """ Run application tests """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.formatter_class = argparse.RawTextHelpFormatter
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        self.parser.add_argument(
            'tags', nargs='*', metavar='TAG',
            help=textwrap.dedent("""\
                List, or comma-separated list of filters to select tests to execute.

                format:  [-][tag][/module][:class][.method][[params]]

                -        blacklist matching tests instead of including them.
                tag      whitelist test classes with a matching `@tagged` decorator.
                         All Test classes have `standard` and `at_install` tags
                         until explicitly removed, see the decorator documentation.
                         '*' will match all tags.
                         Default is 'standard', or '*' if '-' is present.
                module   whitelist test classes from the matching module.
                class    whitelist matching test classes.
                method   whitelist matching test methods.
                params   pass these parameters to a test method that supports them.
                         If negated, the parameter will be passed over as negated.

                Parts of the filter are combined with the OR condition.
                Different filters are combined with the AND condition.

                Examples:
                $ odoo-bin test -at_install,/account,/l10n_it,/l10n_it_edi
                $ odoo-bin test :TestClass.test_func /test_module external
                $ odoo-bin test /web.test_js[mail]
            """))
        self.parser.epilog = textwrap.dedent("""
            Only tests belonging to currently installed modules will be run.

            - `post-install` tests will be executed with the current registry as-is.
            - `at-install` trigger the upgrade of the modules they belong to, and all the modules that depend on them.
        """)

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = []
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]
        config.parse_config(config_args, setup_logging=True)

        db_names = config['db_name']
        if not db_names or len(db_names) > 1:
            self.parser.error("Please provide a single database in the config file")
        dbname = parsed_args.db_name = db_names[0]

        # retrieve installed modules
        registry = Registry.new(dbname)
        with registry.cursor(readonly=True) as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            installed_modules = env['ir.module.module'].search([('state', '=', 'installed')]).mapped("name")

        # build suites
        with PerfCounter("load suite"):
            threading.current_thread().dbname = dbname
            config['test_enable'] = True
            config['test_tags'] = ",".join(parsed_args.tags)
            from odoo.tests import loader as tests_loader  # noqa: PLC0415
            from odoo.tests.result import OdooTestResult  # noqa: PLC0415
            at_install_suite = tests_loader.make_suite(installed_modules, 'at_install')
            post_install_suite = tests_loader.make_suite(installed_modules, 'post_install')

        # compute which modules will need to be upgraded while running at_install tests
        upgrade_modules = {test.test_module for test in at_install_suite._tests}

        server = None
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})

            # if there's at least an `http_case`, generate bundles and start the server
            if at_install_suite.has_http_case() or post_install_suite.has_http_case():
                with PerfCounter("bundles", cr=cr):
                    env['ir.qweb']._pregenerate_assets_bundles()
                    env.cr.commit()
                server = odoo_service.server = odoo_service.ThreadedServer(odoo.http.root)
                server.start()

            # start post-install tests
            report = OdooTestResult()
            with PerfCounter("Post-install tests", assertion_report=report, cr=env.cr):
                try:
                    result = tests_loader.run_suite(post_install_suite, global_report=report)
                    report.update(result)
                    report.log_stats()
                except Exception:
                    _logger.exception("Error while running post-install tests")

        # upgrading the modules, which will trigger at-install tests
        # tags will be re-read from config['test_tags']
        if at_install_suite._tests:
            registry = Registry.new(
                dbname,
                update_module=True,
                upgrade_modules=upgrade_modules,
            )


class PerfCounter:
    def __enter__(self):
        self.log_method("%s started", self.name)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        other = PerfCounter(copy=self)
        self.log_method(other.delta(self))

    def __init__(
        self, name=None, fmt=None, assertion_report=None,
        cr=None, log_method=None, copy=None,
    ):
        self.name = name or (copy and copy.name)
        self.fmt = fmt or (copy and copy.fmt)
        self.assertion_report = assertion_report or (copy and copy.assertion_report)
        self.cr = cr or (copy and copy.cr)
        self.log_method = None
        if log_method:
            self.log_method = log_method
        elif copy:
            self.log_method = copy.log_method
        if not self.log_method:
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            logger_scope = module.__name__ if module else __name__
            logger = logging.getLogger(logger_scope)
            self.log_method = logger.info
        self.counters = Counter({
            'time': time.time(),
            'cursor_queries': self.cr.sql_log_count if self.cr else 0,
            'extra_queries': odoo.sql_db.sql_counter,
            'tests': getattr(self.assertion_report, 'testsRun', 0),
        })

    def delta(self, other):
        delta = self.counters - other.counters
        if 'extra_queries' in delta and 'cursor_queries' in delta:
            delta['extra_queries'] -= delta['cursor_queries']
        delta = {k: v for k, v in delta.items() if v}
        tokens = self.fmt or {
            'name': "{name} finished",
            'time': "{time:.2f}s elapsed",  # noqa: RUF027
            'tests': "{tests} tests",
            'cursor_queries': "{cursor_queries} queries",
            'extra_queries': "{extra_queries} extra",
        }
        tokens = {k: v for k, v in tokens.items() if k in delta or k in ('time', 'name')}
        return ", ".join(fmt.format(**delta, name=self.name) for _k, fmt in tokens.items())
