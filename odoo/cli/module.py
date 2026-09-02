import argparse
import logging
import textwrap
from contextlib import contextmanager
from pathlib import Path

from odoo import SUPERUSER_ID
from odoo.api import Environment
from odoo.cli.command import Command
from odoo.modules.loading import force_demo
from odoo.modules.module import get_module_path, initialize_sys_path
from odoo.modules.registry import Registry
from odoo.tools import OrderedSet, config, parse_version

_logger = logging.getLogger(__name__)

MODULE_TO_CHANGE_DOMAIN = [('state', 'in', ['to install', 'to upgrade', 'to remove'])]


class Module(Command):
    """ Manage modules, install demo data """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subparsers = self.parser.add_subparsers(
            dest='subcommand', required=True,
            help='Subcommands help')

        install_parser = subparsers.add_parser(
            'install',
            help="Install modules",
            description="Install selected modules",
        )
        install_parser.set_defaults(func=self._install)
        upgrade_parser = subparsers.add_parser(
            'upgrade',
            help="Upgrade modules",
            description="Upgrade selected modules",
        )
        upgrade_parser.set_defaults(func=self._upgrade)
        uninstall_parser = subparsers.add_parser(
            'uninstall',
            help="Uninstall modules",
            description="Uninstall selected modules",
        )
        uninstall_parser.set_defaults(func=self._uninstall)
        force_demo_parser = subparsers.add_parser(
            'force-demo',
            help="Install demo data (force)",
            description="Install demonstration data (force)",
        )
        force_demo_parser.set_defaults(func=self._force_demo)
        list_parser = subparsers.add_parser(
            'list',
            help="List modules",
            description="List modules",
        )
        list_parser.set_defaults(func=self._list_modules)

        for parser in (
            install_parser,
            uninstall_parser,
            upgrade_parser,
            force_demo_parser,
            list_parser,
        ):
            parser.formatter_class = argparse.RawDescriptionHelpFormatter
            parser.add_argument(
                '-c', '--config', dest='config',
                help="use a specific configuration file")
            parser.add_argument(
                '-d', '--database', dest='db_name', default=None,
                help="database name, connection details will be taken from the config file")
            parser.add_argument("-D", "--data-dir", dest="data_dir",
                 help="directory where to store Odoo data")
        for parser in (
            install_parser,
            uninstall_parser,
            upgrade_parser,
        ):
            parser.add_argument("-n", "--dry-run", dest="dry_run", action='store_true',
                 help="simulate changes")

        install_parser.add_argument(
            'modules', nargs='+', metavar='MODULE',
            help="names of the modules to be installed. For data modules (.zip), use the path instead")
        install_parser.epilog = textwrap.dedent("""\
            Before installing modules, an Odoo database needs to be created and initialized
            on your PostgreSQL instance, using the `db init` command:

            $ odoo-bin db init <db_name>

            To get help on its parameters, see:

            $ odoo-bin db init --help
        """)
        uninstall_parser.add_argument(
            'modules', nargs='+', metavar='MODULE',
            help="names of the modules to be uninstalled")
        upgrade_parser.add_argument(
            'modules', nargs='+', metavar='MODULE',
            help="name of the modules to be upgraded, use 'base' or 'all' if you want to upgrade everything")
        upgrade_parser.add_argument(
            '--outdated', action='store_true',
            help="only update modules that have a newer version on disk. "
                 "If 'all' is used as `modules` argument, this applies to all installed modules.",
        )

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)
        config_args = ['--no-http']
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]
        if parsed_args.data_dir:
            config_args += ['-D', parsed_args.data_dir]
        config.parse_config(config_args, setup_logging=True)

        db_names = config['db_name']
        if not db_names or len(db_names) > 1:
            self.parser.error("Please provide a single database in the config file")
        parsed_args.db_name = db_names[0]

        parsed_args.func(parsed_args)

    def _get_zip_path(self, path):
        fullpath = Path(path).resolve()
        if fullpath.is_file() and fullpath.suffix.lower() == '.zip':
            return fullpath
        return None

    def _get_module_names(self, module_names):
        """ Get valid module names from disk before starting the Db environment """
        initialize_sys_path()
        return {
            module
            for module in set(module_names)
            if get_module_path(module)
            or self._get_zip_path(module)
        }

    @contextmanager
    def _create_env_context(self, db_name):
        with Registry.new(db_name).cursor() as cr:
            yield Environment(cr, SUPERUSER_ID, {})

    def show_modules(self, modules, show_state=False, show_version=False):
        for module in modules:
            info = [module.name]
            if show_version:
                if module.state == 'to upgrade' and module.latest_version != module.installed_version:
                    info.extend((module.latest_version, '->', module.installed_version))
                elif v := module.latest_version:
                    info.append(v)
            if show_state:
                info.append(f'({module.state})')
            info.extend(('-', module.shortdesc or '(empty)'))
            print(*info)  # noqa: T201

    def _install(self, parsed_args):
        with self._create_env_context(parsed_args.db_name) as env:

            valid_module_names = self._get_module_names(parsed_args.modules)
            Module = env['ir.module.module']
            Module.update_list()
            installable_modules = Module.search([('name', 'in', valid_module_names)])
            if parsed_args.dry_run:
                _logger.info("Dry-run")
                installable_modules.button_install()
                self.show_modules(Module.search(MODULE_TO_CHANGE_DOMAIN))
                env.cr.rollback()
            elif installable_modules:
                installable_modules.button_immediate_install()

            non_installable_modules = OrderedSet(
                module
                for module in parsed_args.modules
                if module not in set(installable_modules.mapped("name"))
            )
            importable_zipfiles = [
                fullpath
                for module in non_installable_modules
                if (fullpath := self._get_zip_path(module))
            ]
            if importable_zipfiles:
                if 'imported' not in env['ir.module.module']._fields:
                    _logger.warning("Cannot import data modules unless the `base_import_module` module is installed")
                elif parsed_args.dry_run:
                    _logger.warning("Dry-run does not support importable zip files")
                else:
                    for importable_zipfile in importable_zipfiles:
                        env['ir.module.module']._import_zipfile(importable_zipfile)

    def _upgrade(self, parsed_args):
        with self._create_env_context(parsed_args.db_name) as env:
            Module = env['ir.module.module']
            Module.update_list()
            if 'all' in parsed_args.modules:
                upgradable_modules = Module.search([('state', '=', 'installed')])
            else:
                valid_module_names = self._get_module_names(parsed_args.modules)
                upgradable_modules = Module.search([('name', 'in', valid_module_names)])
            if parsed_args.outdated:
                upgradable_modules = upgradable_modules.filtered(
                    lambda x: parse_version(x.installed_version) > parse_version(x.latest_version),
                )
            if parsed_args.dry_run:
                _logger.info("Dry-run")
                upgradable_modules.button_upgrade()
                self.show_modules(Module.search(MODULE_TO_CHANGE_DOMAIN), show_version=True)
                env.cr.rollback()
            elif upgradable_modules:
                upgradable_modules.button_immediate_upgrade()

    def _uninstall(self, parsed_args):
        with self._create_env_context(parsed_args.db_name) as env:
            Module = env['ir.module.module']
            if modules := Module.search([('name', 'in', parsed_args.modules)]):
                Module.update_list()
                if parsed_args.dry_run:
                    _logger.info("Dry-run")
                    modules.button_uninstall()
                    self.show_modules(Module.search(MODULE_TO_CHANGE_DOMAIN))
                    env.cr.rollback()
                else:
                    modules.button_immediate_uninstall()

    def _force_demo(self, parsed_args):
        with self._create_env_context(parsed_args.db_name) as env:
            force_demo(env)

    def _list_modules(self, parsed_args):
        with self._create_env_context(parsed_args.db_name) as env:
            Module = env['ir.module.module']
            _logger.info("Listing modules")
            self.show_modules(Module.search([('state', '=', 'installed')]), show_version=True)
            if modules := Module.search(MODULE_TO_CHANGE_DOMAIN):
                self.show_modules(modules, show_state=True, show_version=True)
