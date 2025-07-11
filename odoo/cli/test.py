import argparse
import inspect
import logging
import textwrap
import threading
import time
from collections import Counter
from contextlib import contextmanager
from itertools import chain
from pathlib import Path

import odoo
import odoo.http
import odoo.service.server as odoo_service
from odoo import SUPERUSER_ID
from odoo.api import Environment
from odoo.cli.command import Command
from odoo.modules.registry import Registry
from odoo.tools import config

_logger = logging.getLogger(__name__)


class SubcommandHelpFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, max_help_position=80)


class Test(Command):
    """ Manage application tests """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.formatter_class = argparse.RawTextHelpFormatter
        self.parser.add_argument(
            '-c', '--config', dest='config',
            help="use a specific configuration file")
        self.parser.add_argument(
            '-d', '--database', dest='db_name', default=None,
            help="database name, connection details will be taken from the config file")
        subparsers = self.parser.add_subparsers(
            dest='subcommand', required=True,
            help='Subcommands help')
        run_parser = subparsers.add_parser(
            'run',
            help="Run tests",
            description="Run application tests",
            formatter_class=SubcommandHelpFormatter)
        run_parser.add_argument(
            '--install', nargs="+",
            help="Names of the modules to install (for at-install tests).")
        run_parser.set_defaults(func=self._run)

        search_parser = subparsers.add_parser(
            'search',
            help="Search tests by tags",
            description="Search tests by tags",
            formatter_class=SubcommandHelpFormatter)
        search_parser.add_argument(
            '--modules', action='store_true',
            help="Only output the names of the modules that contain the tests")
        search_parser.epilog = textwrap.dedent("""\
            As this command works on all modules, also those which are not installed,
            it may take up to some minutes for python to compile them all to byte-code
            on the first run. Subsequent calls will be done in a few seconds.
        """)
        search_parser.set_defaults(func=self._search)

        for parser in (run_parser, search_parser):
            parser.add_argument(
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
                        -at_install /account /l10n_it /l10n_it_edi
                        :TestClass.test_func /test_module external
                        /web.test_js[mail]
                """))

    def _run(self, parsed_args):
        from odoo.tests import loader as tests_loader  # noqa: PLC0415
        from odoo.tests.result import OdooTestResult  # noqa: PLC0415

        # 1. eventually install specified modules
        # 2. load the registry
        # 3. run eventual at_install tests
        registry = Registry.new(
            parsed_args.db_name,
            install_modules=parsed_args.install,
            update_module=bool(parsed_args.install),
            new_db_demo=True,
        )
        with registry.cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})

            # Build the post_install_suite
            Module = env['ir.module.module']
            Module.update_list()
            installed_modules = Module.search([('state', '=', 'installed')]).mapped("name")
            post_install_suite = tests_loader.make_suite(installed_modules, 'post_install')
            if post_install_suite._tests:
                # if there's at least an `http_case`, generate bundles and start the server
                if post_install_suite.has_http_case():
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

    def _search(self, parsed_args):
        _logger.info("Searching for tests with tags: %s", " ".join(parsed_args.tags))

        all_modules = sorted(
            p.name
            for base_folder in odoo.addons.__path__
            for p in Path(base_folder).glob('*')
            if p.is_dir() and (p / '__manifest__.py').is_file()
            and p.name not in ('iot_drivers',)  # unloadable module
        )

        from odoo.tests import loader as tests_loader  # noqa: PLC0415
        # build suites
        at_install_suite = tests_loader.make_suite(all_modules, 'at_install')
        post_install_suite = tests_loader.make_suite(all_modules, 'post_install')
        all_tests = chain(at_install_suite, post_install_suite)

        if parsed_args.modules:
            for module in sorted({test.test_module for test in all_tests}):
                print(module)  # noqa: T201
        else:
            for test in all_tests:
                tags = test.test_tags
                tags_str = ','.join(tags) + ',' if tags else ''
                print(f"{tags_str}/{test.test_module}:{test.__class__.__name__}.{test._testMethodName}")  # noqa: T201

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
        threading.current_thread().dbname = dbname

        config['test_enable'] = True
        config['test_tags'] = ",".join(parsed_args.tags)

        parsed_args.func(parsed_args)


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
