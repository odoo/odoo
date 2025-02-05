import csv
import datetime
import logging
from collections import defaultdict
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

def _get_languages(env, lang, force_install=False):
    if lang == '*':
        domain = []
    else:
        domain = ['|', ('code', 'in', lang), ('iso_code', 'in', lang)]
    ResLang = env['res.lang'].with_context(active_test=not force_install)
    res_languages = ResLang.search_fetch(domain, ['code', 'iso_code'])
    if force_install:
        for res_language in res_languages.filtered(lambda lang: not lang.active):
            load_language(env.cr, res_language.code)
    else:
        found_languages_codes = set(res_languages.mapped('code'))
        if missing_languages := set(lang) - found_languages_codes:
            _logger.warning("Languages %s are not installed, export of those is skipped.", missing_languages)
    return res_languages.mapped(lambda x: (x.code, x.iso_code)) if res_languages else []


def _get_language_files(modules, language_codes, export_pot=False):
    codes = [[None, 'pot'] if export_pot else []] + (list(language_codes) if language_codes else [])
    for module, (code, isocode) in product(modules, codes):
        filename = f"{module}.pot" if isocode == 'pot' else f"{isocode}.po"
        filepath = str(Path(odoo.modules.get_module_path(module)) / 'i18n' / filename)
        yield (module, code, filepath)


# Command and Subcommands
# -------------------------------------------------------------------------------- 

class I18nImport(Subcommand):
    description = 'Import i18n files'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument(
            '--database', '-d', dest='db_name', required=True,
            help='Specify the database name.')
        self.parser.add_argument(
            '--lang', '-l', dest='lang', metavar='LANG_CODE', required=True,
            help=('Language ISO code of the files to be imported.'))
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
        self.parser.add_argument('--database', '-d', dest='db_name',
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

        self.parser.add_argument('--install-modules', '-im', dest='install_modules', action='store_true',
            help="Force the install of modules before export on existing database.")

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)

        # Parsing modules arguments
        if not parsed_args.modules:
            raise ValueError(
                "Please select at least one module, "
                "with options: --modules/--all/--community/--enterprise"
            )
        parsed_args.modules = (
            'all' if parsed_args.all
            else 'LGPL-3' if parsed_args.community
            else 'OEEL-1' if parsed_args.enterprise
            else [x for x in parsed_args.modules if x.strip()]
        )
        if isinstance(parsed_args.modules, str):
            all_modules = odoo.modules.module.get_modules()
            if parsed_args.modules == 'all':
                parsed_args.modules = all_modules
            else:
                lic_modules = defaultdict(list)
                for module in all_modules:
                    lic = odoo.modules.module.load_manifest(module)['license']
                    lic_modules[lic].append(module)
                parsed_args.modules = lic_modules[parsed_args.modules]

        # No database specified, create a temporary one
        if not parsed_args.db_name:
            now = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
            parsed_args.db_name = f'i18n_{now}'
            parsed_args.install_modules = True

        # Report configuration
        _logger.info("Modules selected: %s", parsed_args.modules)
        _logger.info("Languages selected: %s", parsed_args.lang)
        if parsed_args.install_modules:
            _logger.info("Selected modules will be forcibly (re-)installed")
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
        if parsed_args.install_modules:
            odoo.tools.config['init'] = {'base': 1}
        odoo.tools.config['without_demo'] = True
        if export_pot := 'pot' in parsed_args.lang:
            pot_idx = parsed_args.lang.index('pot')
            parsed_args.lang.pop(pot_idx)

        # Start a new environment, create/init the database if needed
        with self.build_env(
            parsed_args.db_name,
            allow_create=True,
            update_module=parsed_args.install_modules,
        ) as env:

            # {module: 1 for module in parsed_args.modules}

            language_codes = _get_languages(env, parsed_args.lang, force_install=False)
            language_files = _get_language_files(parsed_args.modules, language_codes, export_pot=export_pot)
            for (module, lang_code, filepath) in language_files:
                self._export_module(env, module, filepath, lang_code, parsed_args.format)

    def _export_module(self, env, module, filepath, lang_code, fmt):
        _logger.info("Exporting %s", filepath)
        with open(filepath, 'wb') as outfile:
            trans_export(lang_code, [module], outfile, fmt, env.cr)


class I18n(Command, SubcommandsMixin):
    """ Import, export, setup internationalization (i18n) files. """
    subcommands = I18nExport, I18nImport
