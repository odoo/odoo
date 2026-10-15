"""Run repeatable business-flow benchmarks on an already prepared database.

Define BenchmarkCase subclasses in an addon's benchmarks package and explicitly
import their modules from benchmarks/__init__.py. Mark methods with @benchmark;
file, class and method names need no prefix. Ordinary test discovery does not
load these benchmarks.

    odoo-bin benchmark -d db -t /sale
    odoo-bin benchmark -d db -t /sale:BenchmarkSaleOrder.confirm --rounds 5
    odoo-bin benchmark -d db --warmups 0 --profile --logfile benchmark.log

Selection uses the test-tag grammar, with benchmark as the default and implicit
positive tag. --warmups and --rounds override decorator and class settings.
--profile saves a separate extra execution in ir.profile. The command reports
medians and query counts; metric values do not determine success. Execution
errors fail the command, while missing fixtures may skip individual benchmarks.
"""

import importlib
import importlib.util
import inspect
import logging
import optparse
import sys
from unittest.mock import patch

from odoo import api, sql_db
from odoo.modules.db import is_initialized
from odoo.modules.registry import Registry
from odoo.service.server import load_server_wide_modules
from odoo.tools import config

from . import Command

_logger = logging.getLogger('odoo.benchmark')


def get_benchmark_modules(addon):
    """Return modules imported by benchmarks/__init__.py, like normal test discovery.

    No filename filtering. Nested modules must be imported into the root package,
    e.g. ``from .pricing import discounts``. Unlisted files are never imported.
    """
    package_name = f'odoo.addons.{addon}.benchmarks'
    spec = importlib.util.find_spec(package_name)
    if spec is None:
        return []
    package = importlib.import_module(package_name)
    return sorted({
        module for module in vars(package).values()
        if inspect.ismodule(module) and module.__name__.startswith(package_name + '.')
    }, key=lambda module: module.__name__)


def build_benchmark_suite(installed, selector):
    """Return an OdooSuite of selected benchmarks from installed addon names.

    ``selector`` is a TagsSelector. Only post-install cases are eligible;
    inherited methods require the same explicit opt-in as ordinary tests.
    """
    # Core command discovery runs before config parsing.
    # Import the test machinery only when building a suite,
    # after test mode is enabled.
    from odoo.tests import BenchmarkCase  # noqa: PLC0415
    from odoo.tests.suite import OdooSuite  # noqa: PLC0415
    from odoo.tests.tag_selector import TagsSelector  # noqa: PLC0415

    cases = []
    position = TagsSelector('post_install', installed)
    for addon in sorted(installed):
        for module in get_benchmark_modules(addon):
            # Discover a class once in its defining module, even if it is
            # imported elsewhere or exposed under several aliases.
            classes = sorted({
                cls for cls in vars(module).values()
                if inspect.isclass(cls) and issubclass(cls, BenchmarkCase)
                and cls.__module__ == module.__name__ and not inspect.isabstract(cls)
            }, key=lambda cls: cls.__name__)
            for cls in classes:
                # Inherited methods are opt-in so a subclass does not silently
                # repeat all of its parent's benchmarks.
                if getattr(cls, 'allow_inherited_tests_method', False):
                    methods = inspect.getmembers(cls, callable)
                else:
                    methods = sorted(vars(cls).items())
                for name, method in methods:
                    if callable(method) and hasattr(method, '_benchmark'):
                        case = cls(name)
                        if position.check(case) and selector.check(case):
                            cases.append(case)
    # Run classes with lower test_sequence first.
    return OdooSuite(sorted(cases, key=lambda case: getattr(type(case), 'test_sequence', 0)))


class Benchmark(Command):
    """Run developer benchmarks on an existing database"""

    def run(self, args):
        self._setup_options()
        self._parse_options(args)
        # Importing odoo.tests initializes test utilities that depend on parsed config.
        from odoo.tests.tag_selector import TagsSelector  # noqa: PLC0415

        # Registry initialization needs test mode for its report and test pools.
        # The dedicated suite owns dispatch; module loading must not run tests.
        config['test_enable'] = True
        # Command discovery imports this file even for other commands and --help.
        # Keep test-only imports here so those paths do not load the test framework.
        from odoo.tests import loader  # noqa: PLC0415
        from odoo.tests.suite import OdooSuite  # noqa: PLC0415

        try:
            self._check_database_prepared(config['db_name'][0])
            load_server_wide_modules()
            # Preserve registry test mode, but let this command own discovery.
            # Restore ordinary discovery before running benchmarks, even on failure.
            with patch.object(loader, 'make_suite', return_value=OdooSuite()):
                registry = Registry.new(config['db_name'][0], update_module=False)
            with registry.cursor() as cr:
                env = api.Environment(cr, api.SUPERUSER_ID, {})
                installed = set(env['ir.module.module'].search([('state', '=', 'installed')]).mapped('name'))
            try:
                selector = TagsSelector(config['test_tags'] or 'benchmark', installed, default_tag='benchmark', strict=True)
            except ValueError as error:
                config.parser.error(str(error))

            suite = build_benchmark_suite(installed, selector)
            cases = list(suite)
            if not cases:
                _logger.error('No benchmarks matched the selection')
                sys.exit(1)

            keys = {}
            for case in cases:
                case._benchmark_keys = keys

            _logger.info('Running %s selected benchmarks', len(cases))
            result = loader.run_suite(suite, global_report=registry._assertion_report)
            registry._assertion_report.update(result)
            if not result.wasSuccessful():
                sys.exit(1)

            if not keys and result.skipped:
                _logger.info('All selected benchmarks were skipped')

        except Exception:
            _logger.exception('Benchmark startup or execution failed')
            sys.exit(1)
        sys.exit(0)

    def _parse_options(self, args):
        """Parse and validate options before opening the database."""
        assert config.parser.has_option('--rounds'), "Call _setup_options() before _parse_options()"
        parser = config.parser
        try:
            config.parse_config(args, setup_logging=True)
        except ValueError as error:
            parser.error(str(error))

        if len(config['db_name']) != 1:
            parser.error('benchmark requires exactly one database (-d)')

        if any(setting in config._cli_options or config[setting] for setting in ('update', 'init', 'reinit')):
            parser.error('Module installation/update requests are not allowed; prepare the database separately')

        for setting, minimum in (('warmups', 0), ('rounds', 1)):
            value = config[f'benchmark_{setting}']
            if value is not None and value < minimum:
                parser.error(f'--{setting} must be >= {minimum}')

        # Test utilities depend on parsed config; command discovery happens earlier.
        from odoo.tests.tag_selector import TagsSelector  # noqa: PLC0415

        try:
            TagsSelector(config['test_tags'] or 'benchmark', default_tag='benchmark', strict=True)
        except ValueError as error:
            parser.error(str(error))

    def _setup_options(self):
        parser = config.parser
        parser.prog = self.prog
        parser.description = (
            "Discover @benchmark methods across installed addons' benchmarks packages. "
            "Select with -t/--test-tags; the default and implicit selection tag is benchmark. "
            "Benchmark filenames are unrestricted. Module updates must be run separately."
        )
        parser.get_option('--test-tags').help = (
            "Select discovered benchmarks with [-][tag][/module][:class][.method]. "
            "Default and implicit positive tag: benchmark. Exclusions alone apply to that default."
        )
        group = optparse.OptionGroup(parser, 'Benchmark options')
        group.add_option('--warmups', dest='benchmark_warmups', type='int', my_default=None,
                         file_loadable=False,
                         help='Override warmup rounds (>= 0); otherwise use code settings.')
        group.add_option('--rounds', dest='benchmark_rounds', type='int', my_default=None,
                         file_loadable=False,
                         help='Override measured rounds (>= 1); otherwise use code settings.')
        group.add_option('--profile', dest='benchmark_profile', action='store_true', my_default=False,
                         file_loadable=False,
                         help='Save one extra execution per benchmark/user as ir.profile records.')
        parser.add_option_group(group)
        config._load_default_options()

    @staticmethod
    def _check_database_prepared(dbname):
        """Reject an unprepared database before Registry.new can apply updates."""
        with sql_db.db_connect(dbname).cursor() as cr:
            if not is_initialized(cr):
                raise ValueError(f'Database {dbname!r} is not initialized; prepare it before benchmarking')
            cr.execute("""
               SELECT name, state
                 FROM ir_module_module
                WHERE state IN ('to install', 'to upgrade', 'to remove')
                ORDER BY name
            """)
            pending = cr.fetchall()
        if pending:
            details = ', '.join(f'{name} ({state})' for name, state in pending)
            raise ValueError(f'Database {dbname!r} has pending module operations: {details}. Prepare it before benchmarking')
