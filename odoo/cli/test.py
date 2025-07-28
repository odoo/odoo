import argparse
import inspect
import logging
import textwrap
import threading
import time
from collections import Counter, defaultdict
from itertools import chain

import odoo.http
import odoo.service.server as odoo_service
from odoo import api, sql_db
from odoo.cli.command import Command, SubcommandHelpFormatter
from odoo.cli.server import (
    check_postgres_user,
    check_root_user,
    ensure_database_exists,
    report_configuration,
)
from odoo.modules.module import Manifest, MissingDependency
from odoo.modules.registry import Registry
from odoo.tools import config

_logger = logging.getLogger(__name__)


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
            '-i', '--install', nargs="+",
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

        # Given the incremental nature of the "load and execute" at_install tests,
        # we cannot know in advance whether there are HttpCase(s) or not.
        # So we start the server anyway.
        check_root_user()
        check_postgres_user()
        ensure_database_exists(parsed_args.db_name)
        report_configuration()
        server = odoo_service.server = odoo_service.ThreadedServer(odoo.http.root)
        server.start()

        registry = Registry.new(
            parsed_args.db_name,
            install_modules=parsed_args.install,
            update_module=bool(parsed_args.install),
        )
        with registry.cursor() as cr:
            env = api.Environment(cr, api.SUPERUSER_ID, {})

            # Build the post_install_suite
            installed_modules = env['ir.module.module'].search([('state', '=', 'installed')]).mapped("name")
            post_install_suite = tests_loader.make_suite(installed_modules, 'post_install')
            if post_install_suite.has_http_case():
                with PerfCounter("bundles", cr=env.cr):
                    env['ir.qweb']._pregenerate_assets_bundles()
                    env.cr.commit()

            # start post-install tests
            report = registry._assertion_report
            with PerfCounter("Post-install tests", assertion_report=report, cr=env.cr):
                try:
                    result = tests_loader.run_suite(post_install_suite, global_report=report)
                    report.update(result)
                    report.log_stats()
                except Exception:
                    _logger.exception("Error while running post-install tests")

    def _try_check_manifest_dependencies(self, manifest):
        try:
            manifest.check_manifest_dependencies()
            return True
        except MissingDependency:
            return False

    def _check_manifests_dependencies(self, manifests):
        all_manifests = manifests.copy()

        inv_dep_tree = defaultdict(set)
        for name, manifest in all_manifests.items():
            for dep in (manifest.get('depends') or []):
                inv_dep_tree[dep].add(name)

        def remove_recursive(name):
            stack = [name]
            while stack:
                current, *stack = stack
                stack += inv_dep_tree.get(current, [])
                manifests.pop(current, None)

        for name, manifest in all_manifests.items():
            if not (
                manifest.get('installable', True)
                and self._try_check_manifest_dependencies(manifest)
            ):
                remove_recursive(name)
        return manifests

    def _search(self, parsed_args):
        _logger.info("Searching for tests with tags: %s", " ".join(parsed_args.tags))
        from odoo.tests import loader as tests_loader  # noqa: PLC0415

        # build suites
        manifests = {manifest.name: manifest for manifest in Manifest.all_addon_manifests()}
        all_modules = list(self._check_manifests_dependencies(manifests).keys())

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
            'extra_queries': sql_db.sql_counter,
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
