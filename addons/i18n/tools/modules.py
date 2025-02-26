"""
List all modules that can be exported, given user constraints.
"""

import logging
from os.path import sep
from pathlib import Path

from odoo.cli.command import Command
from odoo.modules import get_module_path


_logger = logging.getLogger(__name__)


class Modules(Command):

    excluded = (r'%\_test', r'%\_tests', r'test\_%', r'hw\_%')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.env = kwargs.get('env')
        self.parser.add_argument('folder', help="Filter results by folder")

    def _parse_args(self, cmdargs):
        parsed_args, _unknown = self.parser.parse_known_args(args=cmdargs)
        if parsed_args.folder:
            _logger.info("Folder selected: %s", parsed_args.folder)
        return parsed_args

    def run(self, cmdargs):
        try:
            # Ensure arguments are consistent
            parsed_args = self._parse_args(cmdargs)
        except ValueError as e:
            self.parser.print_help()
            Command.die(f'\n{e}\n')

        domain = (
            [('name', 'not =ilike', pattern) for pattern in self.excluded] + [
            '|',
                ('name', '=ilike', r'l10n\_%'),
                ('name', '=ilike', r'%l10n\_%'),
            ('name', '!=', 'l10n_multilang'),
        ])
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

        print(",".join(module_names))

Modules(env=self.env).run(cmdargs=shellargs)

# match parsed_args.l10n:
#     case x if x in BOOL_ONLY:
#         domain += ['|',
#             ('name', '=ilike', r'l10n\_%'),
#             ('name', '=ilike', r'%l10n\_%'),
#             ('name', '!=', 'l10n_multilang'),
#         ]
#     case x if x in BOOL_NO:
#         domain += ['|',
#             ('name', 'not =ilike', r'l10n\_%'),
#             ('name', 'not =ilike', r'%l10n\_%'),
#         ]
