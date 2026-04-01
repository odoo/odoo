from __future__ import annotations

import ast
import json
import logging
import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    log = logging.getLogger(__name__)
    sql_expression_re = re.compile(r"\b_sql_constraints\s*=\s*\[([^\]]+)]")
    ind = ' ' * 4

    def build_sql_object(match):
        # get the tuple of expressions
        try:
            constraints = ast.literal_eval('[' + match.group(1) + ']')
        except SyntaxError:
            # skip if we cannot match
            return match.group(0)
        result = []
        for name, definition, *messages in constraints:
            message = messages[0] if messages else ''
            constructor = 'Constraint'
            if message:
                # format on 2 lines
                message_repr = json.dumps(message)  # so that the message is in double quotes
                args = f"\n{ind * 2}{definition!r},\n{ind * 2}{message_repr},\n{ind}"
            elif len(definition) > 60:
                args = f"\n{ind * 2}{definition!r}"
            else:
                args = repr(definition)
            result.append(f"_{name} = models.{constructor}({args})")
        return f"\n{ind}".join(result)

    for file in file_manager:
        if file.path.suffix != '.py':
            continue
        content = file.content
        content = sql_expression_re.sub(build_sql_object, content)
        if sql_expression_re.search(content):
            log.warning("Failed to replace in file %s", file.path)
        file.content = content
