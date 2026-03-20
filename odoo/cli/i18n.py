import argparse
import logging
import sys
import textwrap
from pathlib import Path

from odoo import SUPERUSER_ID
from odoo.api import Environment
from odoo.cli.command import Command
from odoo.fields import Domain
from odoo.modules import get_module_path
from odoo.modules.registry import Registry
from odoo.tools import OrderedSet, config
from odoo.tools.translate import TranslationImporter, load_language, trans_export

_logger = logging.getLogger(__name__)

EXPORT_EXTENSIONS = ['.po', '.pot', '.tgz', '.csv']
IMPORT_EXTENSIONS = ['.po', '.csv']


class SubcommandHelpFormatter(argparse.RawTextHelpFormatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, max_help_position=80)


class I18n(Command):
    """ Import, export, setup languages and internationalization files """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        subparsers = self.parser.add_subparsers(
            dest='subcommand', required=True,
            help='Subcommands help')

        self.import_parser = subparsers.add_parser(
            'import',
            help="Import i18n files",
            description="Imports provided translation files",
            formatter_class=SubcommandHelpFormatter,
        )
        self.export_parser = subparsers.add_parser(
            'export',
            help="Export i18n files",
            description="Exports language files into the i18n folder of each module",
            formatter_class=SubcommandHelpFormatter,
        )
        self.loadlang_parser = subparsers.add_parser(
            'loadlang',
            help="Load languages",
            description="Loads languages",
            formatter_class=SubcommandHelpFormatter,
        )

        for parser in (self.import_parser, self.export_parser, self.loadlang_parser):
            parser.add_argument(
                '-c', '--config', dest='config',
                help="use a specific configuration file")
            parser.add_argument(
                '-d', '--database', dest='db_name', default=None,
                help="database name, connection details will be taken from the config file")
            parser.epilog = textwrap.dedent("""\
                Language codes must follow the XPG (POSIX) locale format.
                see: https://www.gnu.org/software/libc/manual/html_node/Locale-Names.html

                To list available codes, you can search them querying the database:
                    $ psql -d <dbname> -c "SELECT iso_code FROM res_lang ORDER BY iso_code"

                Examples:
                    odoo-bin i18n loadlang -l en         # English (U.S.)
                    odoo-bin i18n loadlang -l es es_AR   # Spanish (Spain, Argentina)
                    odoo-bin i18n loadlang -l sr@latin   # Serbian (Latin)
            """)

        self.import_parser.add_argument(
            'files', nargs='+', metavar='FILE', type=Path,
            help=f"files to be imported. Allowed extensions: {', '.join(IMPORT_EXTENSIONS)}\n")
        self.import_parser.add_argument(
            '-w', '--overwrite', action='store_true',
            help="overwrite existing terms")
        self.import_parser.add_argument(
            '-l', '--language', dest='language', metavar='LANG', required=True,
            help="language code")

        self.export_parser.add_argument(
            '-l', '--languages', dest='languages', nargs='+', default=['pot'], metavar='LANG',
            help="list of language codes, 'pot' for template (default)")
        self.export_parser.add_argument(
            'modules', nargs='+', metavar='MODULE',
            help="modules to be exported")
        self.export_parser.add_argument(
            '-o', '--output', metavar="FILE", dest='output',
            help=(
                "output only one file with translations from all provided modules\n"
                f"allowed extensions: {', '.join(EXPORT_EXTENSIONS)},"
                " '-' writes a '.po' file to stdout\n"
                "only one language is allowed when this option is active"
            ),
        )

        self.loadlang_parser.add_argument(
            '-l', '--languages', dest='languages', nargs='+', metavar='LANG',
            help="List of language codes to install")

    def run(self, cmdargs):
        parsed_args = self.parser.parse_args(args=cmdargs)

        config_args = ['--no-http']
        if parsed_args.config:
            config_args += ['-c', parsed_args.config]
        if parsed_args.db_name:
            config_args += ['-d', parsed_args.db_name]

        config.parse_config(config_args, setup_logging=True)

        db_names = config['db_name']
        if not db_names or len(db_names) > 1:
            self.parser.error("Please provide a single database in the config file")
        parsed_args.db_name = db_names[0]

        match parsed_args.subcommand:
            case 'import':
                self._import(parsed_args)
            case 'export':
                self._export(parsed_args)
            case 'loadlang':
                self._loadlang(parsed_args)

    def _get_languages(self, env, language_codes, active_test=True):
        # We want to log invalid parameters
        Lang = env['res.lang'].with_context(active_test=False)
        languages = Lang.search(Domain.OR([Domain('iso_code', 'in', language_codes),
                                           Domain('code', 'in', language_codes)]))
        if not_found_language_codes := set(language_codes) - set(languages.mapped("iso_code")):
            _logger.warning("Ignoring not found languages: %s", ', '.join(not_found_language_codes))
        if active_test:
            if not_installed_languages := languages.filtered(lambda x: not x.active):
                languages -= not_installed_languages
                iso_codes = not_installed_languages.mapped('iso_code')
                _logger.warning(
                    textwrap.dedent("""\
                        Ignoring not installed languages: %s
                        Install them running the below command, then run this command again.

                        $ %s -l %s
                    """),
                    ', '.join(iso_codes),
                    self.loadlang_parser.prog,
                    ' '.join(iso_codes),
                )
        return languages

    def _import(self, parsed_args):
        paths = OrderedSet(parsed_args.files)
        if invalid_paths := [path for path in paths if (
            not path.exists()
            or path.suffix not in IMPORT_EXTENSIONS
        )]:
            _logger.warning("Ignoring invalid paths: %s",
                ', '.join(str(path) for path in invalid_paths))
            paths -= set(invalid_paths)
        if not paths:
            self.import_parser.error("No valid path was provided")

        with Registry(parsed_args.db_name).cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            translation_importer = TranslationImporter(cr)
            language = self._get_languages(env, [parsed_args.language])
            if not language:
                self.import_parser.error("No valid language has been provided")
            for path in paths:
                with path.open("rb") as infile:
                    translation_importer.load(infile, path.suffix.removeprefix('.'), language.code)
            translation_importer.save(overwrite=parsed_args.overwrite)

    def _export(self, parsed_args):
        export_pot = 'pot' in parsed_args.languages

        if parsed_args.output:
            if len(parsed_args.languages) != 1:
                self.export_parser.error(
                    "When --output is specified, one single --language must be supplied")
            if parsed_args.output != '-':
                parsed_args.output = Path(parsed_args.output)
                if parsed_args.output.suffix not in EXPORT_EXTENSIONS:
                    self.export_parser.error(
                        f"Extensions allowed for --output are {', '.join(EXPORT_EXTENSIONS)}")
                if export_pot and parsed_args.output.suffix == '.csv':
                    self.export_parser.error(
                        "Cannot export template in .csv format, please specify a language.")

        if export_pot:
            parsed_args.languages.remove('pot')

        with Registry(parsed_args.db_name).cursor(readonly=True) as cr:
            env = Environment(cr, SUPERUSER_ID, {})

            # We want to log invalid parameters
            modules = env['ir.module.module'].search_fetch(
                [('name', 'in', parsed_args.modules)], ['name', 'state'])
            if not_found_module_names := set(parsed_args.modules) - set(modules.mapped("name")):
                _logger.warning("Ignoring not found modules: %s",
                    ", ".join(not_found_module_names))
            if not_installed_modules := modules.filtered(lambda x: x.state != 'installed'):
                _logger.warning("Ignoring not installed modules: %s",
                    ", ".join(not_installed_modules.mapped("name")))
                modules -= not_installed_modules
            if len(modules) < 1:
                self.export_parser.error("No valid module has been provided")
            module_names = modules.mapped("name")

            languages = self._get_languages(env, parsed_args.languages)
            languages_count = len(languages) + export_pot
            if languages_count == 0:
                self.export_parser.error("No valid language has been provided")

            if parsed_args.output:
                self._export_file(env, module_names, languages.code, parsed_args.output)
            else:
                # Po(t) files in the modules' i18n folders
                for module_name in module_names:
                    i18n_path = Path(get_module_path(module_name), 'i18n')
                    if export_pot:
                        path = i18n_path / f'{module_name}.pot'
                        self._export_file(env, [module_name], None, path)
                    for language in languages:
                        path = i18n_path / f'{language.iso_code}.po'
                        self._export_file(env, [module_name], language.code, path)

    def _export_file(self, env, module_names, lang_code, path):
        source = module_names[0] if len(module_names) == 1 else 'modules'
        destination = 'stdout' if path == '-' else path
        _logger.info("Exporting %s (%s) to %s", source, lang_code or 'pot', destination)

        if destination == 'stdout':
            if not trans_export(lang_code, module_names, sys.stdout.buffer, 'po', env):
                _logger.warning("No translatable terms were found in %s.", module_names)
            return

        path.parent.mkdir(exist_ok=True)
        export_format = path.suffix.removeprefix('.')
        if export_format == 'pot':
            export_format = 'po'
        with path.open('wb') as outfile:
            if not trans_export(lang_code, module_names, outfile, export_format, env):
                _logger.warning("No translatable terms were found in %s.", module_names)

    def _loadlang(self, parsed_args):
        with Registry(parsed_args.db_name).cursor() as cr:
            env = Environment(cr, SUPERUSER_ID, {})
            for language in self._get_languages(env, parsed_args.languages, active_test=False):
                load_language(env.cr, language.code)
