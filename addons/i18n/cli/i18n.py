import csv
import logging
from itertools import product
from pathlib import Path

import odoo
from odoo.cli.command import Command, SubcommandsMixin, Subcommand
from odoo.tools.translate import trans_export, load_language


"""
    Import, export, setup internationalization files

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
        o i18n export l10n_it_edi

    import:
        o i18n import \
          --database=odoodb \
          --files 
          --community / --enterprise / --all / [MODULE,...]

"""


_logger = logging.getLogger(__name__)


def _get_languages(env, lang):
    if lang == '*':
        domain = []
    else:
        domain = ['|', ('code', 'in', lang), ('iso_code', 'in', lang)]
    return env['res.lang'].with_context(active_test=False).search_fetch(domain, ['code', 'iso_code'])


def _get_language_files(env, module_names, language_codes, export_pot=False):
    codes = [[None, 'pot'] if export_pot else []] + (list(language_codes) if language_codes else [])
    modules_map = {m.name: m for m in env['ir.module.module'].search([('name', 'in', module_names)])}
    for module_name, (code, isocode) in product(module_names, codes):
        if module := modules_map.get(module_name):
            filename = f"{module_name}.pot" if isocode == 'pot' else f"{isocode}.po"
            filepath = str(Path(odoo.modules.get_module_path(module_name)) / 'i18n' / filename)
            yield (module, code, filepath)


# Command and Subcommands
# -------------------------------------------------------------------------------- 

class I18nList(Subcommand):
    description = "List i18n-exportable modules"
    excluded = (r'%\_test', r'%\_tests', r'test\_%', r'hw\_%', 'l10n_be_codabox')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser.add_argument('--database', '-d', dest='db_name', required=True,
            help="Specify the database name.")
        self.parser.add_argument('--delimiter', default='\n',
            help="Delimiter between modules, default='\n'")
        modules_group = self.parser.add_argument_group('Module options (mutually exclusive)')
        modules_parser = modules_group.add_mutually_exclusive_group(required=True)
        modules_parser.add_argument('--community', action='store_true',
            help="List all i18n-exportable community modules")
        modules_parser.add_argument('--enterprise', action='store_true',
            help="List all i18n-exportable enterprise modules")
        modules_parser.add_argument('--l10n', action='store_true',
            help="List all i18n-exportable l10n modules")

    def run(self, cmdargs):
        try:
            # Ensure arguments are consistent
            parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        # Start a new environment, create/init the database if needed
        logging.disable(logging.CRITICAL)
        try:
            with self.build_env(parsed_args.db_name) as env:
                logging.disable(logging.NOTSET)
                domain = [('name', 'not =ilike', pattern) for pattern in self.excluded]
                if parsed_args.community:
                    domain += [('license', '=', 'LGPL-3')]
                elif parsed_args.enterprise:
                    domain += [('license', '=', 'OEEL-1')]
                elif parsed_args.l10n:
                    domain += [('name', '=ilike', r'l10n\_%')]
                modules = env['ir.module.module'].search_fetch(domain, ['name'], order="name")
                module_names = modules.mapped("name")
                print(parsed_args.delimiter.join(module_names))
        except Exception as e:
            Command.die(f"Error retrieving modules: {e}")


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
        self.parser.add_argument('modules', nargs='*',
            metavar='MODULE,...', help=("Comma-separated list of modules to be exported"))

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)

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
        language_files = _get_language_files(env, modules, language_codes, export_pot=export_pot)
        for (module, lang_code, filepath) in language_files:
            self._export_module(env, module, filepath, lang_code, exp_format)

    def _export_module(self, env, module, filepath, lang_code, fmt):
        if not module or module.state != 'installed':
            _logger.info("Module %s is not installed, skipping", module)
            return
        _logger.info("Exporting %s", filepath)
        i18n_path = Path(filepath).parent
        if not i18n_path.exists():
            _logger.info(
                "Module '%s' has no i18n folder, skipping. "
                "Create one if you want to export.",
                module.name,
            )
            return
        with open(filepath, 'wb') as outfile:
            trans_export(lang_code, [module.name], outfile, fmt, env.cr)



class I18n(Command, SubcommandsMixin):
    """ Import, export, setup languages and internationalization files """
    subcommands = I18nExport, I18nImport, I18nAddLang, I18nList
