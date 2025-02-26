from os.path import sep
from pathlib import Path

from odoo.cli.command import Command
from odoo.modules import get_module_path


BOOL_YES = {'1', 'yes', 'true', 'on'}
BOOL_NO = {'0', 'no', 'false', 'off'}
BOOL_ONLY = {'only'}
YES_NO_ONLY = BOOL_YES | BOOL_NO | BOOL_ONLY


class Modules(Command):
    """
    List all modules that can be exported, given user constraints.

    This command is not shown on `help` because it's not imported by the `__init__.py` file.
    We can use it by passing the file through the `odoo-bin shell`.

    ./odoo-bin \
        --addons-path=odoo/addons,addons,../enterprise \
        shell                                          \
        -c ../.odoorc                                  \
        --log-level=error                              \
        --                                             \
        --delimiter='\n'                               \
        --folder=/home/odoo/work/odoo                  \
        < addons/i18n/tools/modules.py
    """
    excluded = (r'%\_test', r'%\_tests', r'test\_%', r'hw\_%')

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.env = kwargs.get('env')
        self.parser.add_argument('--delimiter', default=',', help="Delimiter")
        self.parser.add_argument('--folder', help="Filter results by folder")
        self.parser.add_argument(
            '--l10n', choices=YES_NO_ONLY, default='yes',
            help="Filter results by folder")

    def run(self, cmdargs):
        try:
            parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        match parsed_args.delimiter:
            case '\\n':
                parsed_args.delimiter = '\n'
            case '\\r':
                parsed_args.delimiter = '\r'
            case '\\r\\n':
                parsed_args.delimiter = '\r\n'

        domain = [('name', 'not =ilike', pattern) for pattern in self.excluded]
        match parsed_args.l10n:
            case x if x in BOOL_ONLY:
                domain += ['|',
                    ('name', '=ilike', r'l10n\_%'),
                    ('name', '=ilike', r'%l10n\_%'),
                    ('name', '!=', 'l10n_multilang'),
                ]
            case x if x in BOOL_NO:
                domain += ['|',
                    ('name', 'not =ilike', r'l10n\_%'),
                    ('name', 'not =ilike', r'%l10n\_%'),
                ]
            case x if x in BOOL_YES:
                domain += [
                    '|',
                        ('name', '=ilike', r'l10n\_%'),
                        ('name', '=ilike', r'%l10n\_%'),
                    ('name', '!=', 'l10n_multilang'),
                ]
        modules = self.env['ir.module.module'].search_fetch(domain, ['name'], order="name")
        module_names = modules.mapped("name")

        if parsed_args.folder:
            base_path = f"{Path(parsed_args.folder).resolve()}{sep}"
        to_filter, module_names = module_names, []
        for module_name in to_filter:
            if parsed_args.folder:
                if not (module_path := get_module_path(module_name, display_warning=False)):
                    continue
                module_path = Path(module_path).resolve()
                if str(module_path).startswith(base_path):
                    module_names.append(module_name)
            else:
                module_names.append(module_name)

        print(parsed_args.delimiter.join(module_names))


Modules(env=self.env).run(cmdargs=shellargs)
