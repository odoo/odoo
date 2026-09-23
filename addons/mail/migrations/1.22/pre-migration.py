import ast
import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)


def migrate(cr: Cursor, version: str | None) -> None:
    cr.execute(
        "SELECT id, alias_defaults FROM mail_alias WHERE alias_defaults IS NOT NULL"
    )
    broken = []
    for alias_id, defaults in cr.fetchall():
        try:
            parsed = ast.literal_eval(defaults)
        except SyntaxError, ValueError, TypeError, MemoryError, RecursionError:
            broken.append(alias_id)
            continue
        if not isinstance(parsed, dict):
            broken.append(alias_id)
    if not broken:
        return
    cr.execute(
        "UPDATE mail_alias SET alias_defaults = '{}' WHERE id = ANY(%s)", (broken,)
    )
    _logger.info(
        "mail 1.22: reset alias_defaults on %d alias(es) that did not hold a python "
        "dict; the mail gateway was already ignoring those values.",
        len(broken),
    )
