import logging

from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_TABLE = "credential_access_log"
_MODEL = "credential.access.log"
_COLUMNS = ("session_id", "user_agent")


def _rows_carrying_a_value(cr, column):
    cr.execute(
        SQL(
            "SELECT count(*) FROM %s WHERE %s IS NOT NULL",
            SQL.identifier(_TABLE),
            SQL.identifier(column),
        )
    )
    return cr.fetchone()[0]


def migrate(cr, version):
    if not version:
        return
    if not table_exists(cr, _TABLE):
        return

    for column in _COLUMNS:
        if not column_exists(cr, _TABLE, column):
            continue

        populated = _rows_carrying_a_value(cr, column)
        if populated:
            _logger.warning(
                "%s.%s holds %s non-empty row(s) and was NOT dropped. This column is "
                "written by no code in this fork, so something outside it is filling "
                "the audit trail; investigate before removing the column.",
                _TABLE,
                column,
                populated,
            )
            continue

        cr.execute(
            """
            DELETE FROM ir_model_fields f
                  USING ir_model m
                  WHERE f.model_id = m.id
                    AND f.name = %s
                    AND m.model = %s
            """,
            (column, _MODEL),
        )
        removed = cr.rowcount
        cr.execute(
            SQL(
                "ALTER TABLE %s DROP COLUMN IF EXISTS %s",
                SQL.identifier(_TABLE),
                SQL.identifier(column),
            )
        )
        _logger.info(
            "%s: dropped empty column %s (%s field definition(s) removed)",
            _TABLE,
            column,
            removed,
        )
