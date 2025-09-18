import logging
import typing
from collections.abc import Iterable, Iterator
from contextlib import suppress

from odoo.tools.misc import file_open

if typing.TYPE_CHECKING:
    from odoo.db import Cursor

_logger = logging.getLogger(__name__)


def get_installed_modules(cursor: Cursor) -> list[str]:
    cursor.execute("""
        SELECT name
          FROM ir_module_module
         WHERE state IN ('installed', 'to upgrade', 'to remove');
    """)
    return [result[0] for result in cursor.fetchall()]


def get_neutralization_queries(modules: Iterable[str]) -> Iterator[str]:
    # neutralization for each module
    for module in modules:
        filename = f"{module}/data/neutralize.sql"
        with suppress(FileNotFoundError):
            with file_open(filename) as file:
                yield file.read().strip()


def neutralize_database(cursor: Cursor) -> None:
    installed_modules = get_installed_modules(cursor)
    queries = get_neutralization_queries(installed_modules)
    for query in queries:
        cursor.execute(query)
    _logger.info("Neutralization finished")
