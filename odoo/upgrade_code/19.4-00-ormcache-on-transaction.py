from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    clear_cache_re = re.compile(r"\bregistry\.clear_cache")

    for file in file_manager:
        if file.path.suffix != '.py':
            continue
        content = file.content
        content = clear_cache_re.sub(r'transaction.invalidate_ormcache', content)
        file.content = content
