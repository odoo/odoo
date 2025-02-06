import csv
import logging
from collections import defaultdict
from fnmatch import fnmatch
from itertools import product
from pathlib import Path

import odoo
from odoo.cli.command import Command, SubcommandsMixin, Subcommand
from odoo.tools.translate import trans_export, load_language


"""
    Import, export, setup internationalization (i18n) files.

    alias o="odoo/odoo-bin --addons-path=odoo,odoo/odoo,enterprise $*"

    export:
        o i18n export \
          --database='temp_i18n' # if not specified, use a tempdb and delete after \
          --format=[po,tgz,csv]  # default po \
          --community / --enterprise / --all / [MODULE,...]
    example:
        o i18n export --community
        o i18n export --enterprise
        o i18n export --all 
        o i18n export --modules l10n_it_edi

    import:
        o i18n import \
          --database=odoodb \
          --files 
          --community / --enterprise / --all / [MODULE,...]

"""


_logger = logging.getLogger(__name__)


# Helpers
# -------------------------------------------------------------------------------- 

def _get_languages(env, lang):
    if lang == '*':
        domain = []
    else:
        domain = ['|', ('code', 'in', lang), ('iso_code', 'in', lang)]
    return env['res.lang'].with_context(active_test=False).search_fetch(domain, ['code', 'iso_code'])


def _get_language_files(modules, language_codes, export_pot=False):
    codes = [[None, 'pot'] if export_pot else []] + (list(language_codes) if language_codes else [])
    for module, (code, isocode) in product(modules, codes):
        filename = f"{module}.pot" if isocode == 'pot' else f"{isocode}.po"
        filepath = str(Path(odoo.modules.get_module_path(module)) / 'i18n' / filename)
        yield (module, code, filepath)


# Command and Subcommands
# -------------------------------------------------------------------------------- 

class I18nAddLang(Subcommand):
    description = 'Install languages'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument(
            'languages', nargs='*',
            help=('List of ISO codes to be installed.'))
        self.parser.add_argument(
            '--database', '-d', dest='db_name', required=True,
            help='Specify the database name.')

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        _logger.info("Languages selected: %s", parsed_args.languages)
        _logger.info("Connecting to database '%s'" % parsed_args.db_name)
        return parsed_args

    def run(self, cmdargs):
        _logger.info("Installing languages...")

        try:
            # Ensure arguments are consistent
            parsed_args = self._parse_args(cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        # Configure Odoo
        odoo.tools.config['without_demo'] = True

        # Start a new environment, create/init the database if needed
        with self.build_env(parsed_args.db_name) as env:
            for language in _get_languages(env, parsed_args.languages):
                load_language(env.cr, language.code)


class I18nImport(Subcommand):
    description = 'Import i18n files'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument(
            '--database', '-d', dest='db_name', required=True,
            help='Specify the database name')
        self.parser.add_argument(
            '--files', '-f', dest='files', metavar='FILE,...', nargs='*', required=True,
            help=("Files to import"))
        self.parser.add_argument('--only-new', '-n', dest='only_new', action='store_true',
            help=("Overwrite"))

    def run(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)

        if parsed_args.format == 'csv':
            # The default limit for CSV fields in the module is 128KiB, which is not
            # quite sufficient to import images to store in attachment. 500MiB is a
            # bit overkill, but better safe than sorry
            csv.field_size_limit(500 << 20)

        with self.build_env(parsed_args.db_name) as env:
            translation_importer = odoo.tools.translate.TranslationImporter(env.cr)
            for filename in parsed_args.files:
                translation_importer.load_file(filename, parsed_args.lang)
            translation_importer.save(overwrite=not parsed_args.only_new)


class I18nExport(Subcommand):
    description = "Export i18n files"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_parser()

    def _setup_parser(self):
        self.parser.add_argument('--database', '-d', dest='db_name', required=True,
            help="Specify the database name.")
        self.parser.add_argument(
            '--format', '-f', dest='format', default='po', choices=('po', 'tgz', 'csv'),
            help=("Export format, default 'po'"))

        self.parser.add_argument(
            '--lang', '-l', dest='lang', nargs='*', default=['pot'], metavar='LANG,...',
            help=("List of language ISO codes to be exported, default 'pot' for template"))

        modules_group = self.parser.add_argument_group('Module options (mutually exclusive)')
        modules_parser = modules_group.add_mutually_exclusive_group()
        modules_parser.add_argument('--modules', '-m', dest='modules', default='', nargs='*',
            metavar='MODULE,...', help=("Comma-separated list of modules to be exported"))
        modules_parser.add_argument('--all', dest='all', action='store_true',
            help=("Export all modules"))
        modules_parser.add_argument('--community', dest='community', action='store_true',
            help=("Export all community modules"))
        modules_parser.add_argument('--enterprise', dest='enterprise', action='store_true',
            help=("Export all enterprise modules"))

    def _parse_args_modules(self, parsed_args):
        all_modules = odoo.modules.module.get_modules()
        if parsed_args.all:
            return all_modules
        elif parsed_args.community or parsed_args.enterprise:
            license_name = 'LGPL-3' if parsed_args.community else 'OEEL-1'
            lic_modules = defaultdict(list)
            for module in all_modules:
                lic = odoo.modules.module.load_manifest(module)['license']
                lic_modules[lic].append(module)
            return lic_modules[license_name]
        else:
            modules = set()
            for module_pattern in parsed_args.modules:
                modules |= {module for module in all_modules if fnmatch(module, module_pattern)}
            return list(modules)

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)

        # Parsing modules arguments
        parsed_args.modules = self._parse_args_modules(parsed_args)

        # Report configuration
        _logger.info("Modules selected: %s", parsed_args.modules)
        _logger.info("Languages selected: %s", parsed_args.lang)
        _logger.info("Connecting to database '%s'" % parsed_args.db_name)

        return parsed_args

    def run(self, cmdargs):
        _logger.info("Exporting i18n files...")

        try:
            # Ensure arguments are consistent
            parsed_args = self._parse_args(cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        # Configure Odoo
        odoo.tools.config['without_demo'] = True
        if export_pot := 'pot' in parsed_args.lang:
            pot_idx = parsed_args.lang.index('pot')
            parsed_args.lang.pop(pot_idx)

        # Start a new environment, create/init the database if needed
        with self.build_env(parsed_args.db_name) as env:
            self._export(env, parsed_args.lang, parsed_args.modules, parsed_args.format, export_pot)

    def _export(self, env, lang, modules, exp_format, export_pot):
        language_codes = _get_languages(env, lang)
        language_files = _get_language_files(modules, language_codes, export_pot=export_pot)
        for (module, lang_code, filepath) in language_files:
            self._export_module(env, module, filepath, lang_code, exp_format)

    def _export_module(self, env, module, filepath, lang_code, fmt):
        module_instance = env['ir.module.module'].search([('name', '=', module)])
        if module_instance and module_instance.state == 'installed':
            _logger.info("Exporting %s", filepath)
            with open(filepath, 'wb') as outfile:
                trans_export(lang_code, [module], outfile, fmt, env.cr)
        else:
            _logger.info("Module %s is not installed, skipping", module)



class I18n(Command, SubcommandsMixin):
    """ Import, export, setup languages and internationalization (i18n) files. """
    subcommands = I18nExport, I18nImport, I18nAddLang
