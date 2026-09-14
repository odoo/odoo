import logging

from odoo.db.schema import column_exists, table_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_TABLE = "integration_service"
_MODEL = "integration.service"
_COLUMN = "request_format"


def _endpoints_declaring_a_non_json_format(cr):
    cr.execute(
        SQL(
            """
            SELECT code, %s
              FROM %s
             WHERE %s IS NOT NULL
               AND %s <> 'json'
             ORDER BY code
            """,
            SQL.identifier(_COLUMN),
            SQL.identifier(_TABLE),
            SQL.identifier(_COLUMN),
            SQL.identifier(_COLUMN),
        )
    )
    return cr.fetchall()


def migrate(cr, version):
    if not version:
        return
    if not table_exists(cr, _TABLE):
        return
    if not column_exists(cr, _TABLE, _COLUMN):
        return

    for code, declared in _endpoints_declaring_a_non_json_format(cr):
        _logger.info(
            "integration: endpoint %r declared %s=%r. No code has ever read the "
            "field: the body and its Content-Type come from the caller's json= / "
            "data= keyword. Check that this endpoint's caller builds the payload "
            "itself before assuming the transport did it.",
            code,
            _COLUMN,
            declared,
        )

    cr.execute(
        """
        DELETE FROM ir_model_fields f
              USING ir_model m
              WHERE f.model_id = m.id
                AND f.name = %s
                AND m.model = %s
        """,
        (_COLUMN, _MODEL),
    )
    removed = cr.rowcount
    cr.execute(
        SQL(
            "ALTER TABLE %s DROP COLUMN IF EXISTS %s",
            SQL.identifier(_TABLE),
            SQL.identifier(_COLUMN),
        )
    )
    _logger.info(
        "%s: dropped %s (%s field definition(s) removed)",
        _TABLE,
        _COLUMN,
        removed,
    )
