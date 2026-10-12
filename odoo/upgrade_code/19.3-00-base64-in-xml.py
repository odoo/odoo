from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    b_re = re.compile(r'type="base64"(.*file=|\n.*file=)')

    for file in file_manager:
        if file.path.suffix != '.xml':
            continue
        content = file.content
        content = b_re.sub(r'type="bytes"\1', content)
        file.content = content
