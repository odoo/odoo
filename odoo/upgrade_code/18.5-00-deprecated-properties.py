from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    model_properties_re = re.compile(r"\._(cr|uid|context)\b")

    for file in file_manager:
        if file.path.suffix != '.py':
            continue
        content = file.content
        content = model_properties_re.sub(r'.env.\1', content)
        file.content = content
