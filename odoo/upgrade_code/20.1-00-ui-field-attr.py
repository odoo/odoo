from __future__ import annotations

import re
import typing

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager


def upgrade(file_manager: FileManager):
    domain_re = re.compile(r'(?:One2many|Many2many|Many2one).*((?:\n {8}.*){0,8}?)\b(domain)=[\'"]')
    required_re = re.compile(r'(?:One2many|Many2many).*((?:\n {8}.*){0,8}?)\b(required)=True')

    def domain_sub(match):
        return match[0].replace('domain=', 'ui_domain=')

    def required_sub(match):
        return match[0].replace('required=True', 'ui_required=True')

    for file in file_manager:
        if file.path.suffix != '.py':
            continue
        content = file.content
        content = domain_re.sub(domain_sub, content)
        content = required_re.sub(required_sub, content)
        file.content = content
