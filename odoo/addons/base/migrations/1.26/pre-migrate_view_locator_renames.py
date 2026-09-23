import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

RENAMES = {
    "action_open_versions": "action_view_versions",
    "action_open_goals": "action_view_goals",
    "action_open_work_entries": "action_view_work_entries",
    "action_open_manufacturing_order": "action_view_manufacturing_order",
    "module_account_payment": "module_account_payment_provider",
}


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return

    for old, new in RENAMES.items():
        cr.execute(
            r"""
            UPDATE ir_ui_view
               SET arch_db = regexp_replace(
                       arch_db::text, '\y' || %s || '\y', %s, 'g'
                   )::jsonb
             WHERE arch_db::text ~ ('\y' || %s || '\y')
            """,
            (old, new, old),
        )
        if cr.rowcount:
            _logger.info("Renamed %s -> %s in %d view(s)", old, new, cr.rowcount)
