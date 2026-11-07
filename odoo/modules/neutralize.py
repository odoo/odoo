# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

import logging
import typing
from contextlib import suppress

from odoo.tools.misc import file_open, topological_sort

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from odoo.sql_db import Cursor

_logger = logging.getLogger(__name__)


def get_installed_modules(cursor: Cursor) -> list[str]:
    """ Return the installed modules, each one after the modules it depends
    on, so that the neutralization of a module can rely on the neutralization
    of its dependencies, and refine it.
    """
    cursor.execute('''
        SELECT m.name, ARRAY_AGG(d.name ORDER BY d.name) FILTER (WHERE d.name IS NOT NULL)
          FROM ir_module_module m
     LEFT JOIN ir_module_module_dependency d ON d.module_id = m.id
         WHERE m.state IN ('installed', 'to upgrade', 'to remove')
      GROUP BY m.name
      ORDER BY m.name
    ''')
    return topological_sort({name: dependencies or () for name, dependencies in cursor.fetchall()})


def get_neutralization_queries(modules: Iterable[str]) -> Iterator[str]:
    # neutralization for each module
    for module in modules:
        filename = f'{module}/data/neutralize.sql'
        with suppress(FileNotFoundError):
            with file_open(filename) as file:
                yield file.read().strip()


def neutralize_database(cursor: Cursor) -> None:
    installed_modules = get_installed_modules(cursor)
    queries = get_neutralization_queries(installed_modules)
    for query in queries:
        cursor.execute(query)
    _logger.info("Neutralization finished")
