"""
List all modules that can be exported, given user constraints.
"""

from os.path import sep
from pathlib import Path

from odoo.modules import get_module_path


self = locals().get('self') or object()

# TODO: parse args


excluded = (r'%\_test', r'%\_tests', r'test\_%', r'hw\_%')
domain = (
    [('name', 'not =ilike', pattern) for pattern in excluded] + [
    '|',
        ('name', '=ilike', r'l10n\_%'),
        ('name', '=ilike', r'%l10n\_%'),
    ('name', '!=', 'l10n_multilang'),
])
modules = self.env['ir.module.module'].search_fetch(domain, ['name'], order="name")
module_names = modules.mapped("name")

if folder:
    base_path = f"{Path(folder).resolve()}{sep}"
to_filter, module_names = module_names, []
for module_name in to_filter:
    if folder:
        if not (module_path := get_module_path(module_name, display_warning=False)):
            continue
        module_path = Path(module_path).resolve()
        if str(module_path).startswith(base_path):
            module_names.append(module_name)
    else:
        module_names.append(module_name)

print(",".join(module_names))

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
