"""
Remove the per-view month/year range attributes of `date` search filters.

They are not parsed anymore, nor accepted by the RNG.

    - <filter name="date" date="date" start_month="-2" end_month="0" start_year="-1" end_year="0"/>
    + <filter name="date" date="date"/>
"""
from __future__ import annotations

import typing

from odoo.upgrade_code.tools_etree import update_etree

if typing.TYPE_CHECKING:
    from odoo.cli.upgrade_code import FileManager

REMOVED_ATTRIBUTES = ('start_month', 'end_month', 'start_year', 'end_year')


def upgrade(file_manager: FileManager):
    files = [
        file for file in file_manager
        if file.path.suffix == '.xml'
        if any(attr in file.content for attr in REMOVED_ATTRIBUTES)
    ]
    if not files:
        return

    def process(root):
        for node in root.iter('filter'):
            for attr in REMOVED_ATTRIBUTES:
                node.attrib.pop(attr, None)

    for fileno, file in enumerate(files, start=1):
        file.content = update_etree(file.content, process)
        file_manager.print_progress(fileno, len(files))
