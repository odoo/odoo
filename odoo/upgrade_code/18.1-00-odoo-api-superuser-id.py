from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    import_re = re.compile(r'from odoo import(.*?SUPERUSER_ID.*?)$', re.MULTILINE)
    usage_re = re.compile(r'odoo.SUPERUSER_ID')

    for file in file_manager:
        if file.path.suffix != '.py' or file.path.parent.name == 'upgrade_code':
            continue
        content = file.content
        content = usage_re.sub('odoo.api.SUPERUSER_ID', content)
        if m := import_re.search(content):
            # move the import of SUPERUSER_ID
            imports = m.group(1).split(',')
            imports = [imp.strip() for imp in imports if 'SUPERUSER_ID' not in imp]
            line = 'from odoo.api import SUPERUSER_ID'
            if imports:
                import_line = ', '.join(imports)
                if 'api' in imports:
                    # we have api, just use it and replace the rest of the file
                    line = f'from odoo import {import_line}'
                    content = content[:m.end()] + content[m.end():].replace('SUPERUSER_ID', 'api.SUPERUSER_ID')
                else:
                    # add a new line with the import (default)
                    line = f'from odoo import {import_line}\n{line}'
            content = content.replace(m.group(0), line)
        file.content = content
