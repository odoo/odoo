import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

OLD = "action_open_code_history"
NEW = "action_view_code_history"


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return

    cr.execute(
        """
        UPDATE ir_ui_view
           SET arch_db = replace(arch_db::text, %s, %s)::jsonb
         WHERE arch_db::text LIKE %s
        """,
        (OLD, NEW, f"%{OLD}%"),
    )
    if cr.rowcount:
        _logger.info(
            "Renamed %s -> %s in %d stored view arch(s)", OLD, NEW, cr.rowcount
        )
