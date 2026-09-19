import logging

from odoo.db.schema import table_exists
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def move_rows_into_subtype_table(cr, kind_code: str, table: str) -> int:
    """Parent to child is a DELETE and an INSERT, because PostgreSQL moves no
    row between them. An id survives it only because the whole tree shares one
    sequence, and the DELETE is possible only because the root holds no
    foreign key into it."""
    if not table_exists(cr, table):
        return 0
    cr.execute("SELECT id FROM resource_asset_kind WHERE code = %s", [kind_code])
    row = cr.fetchone()
    if not row:
        return 0
    cr.execute(
        SQL(
            """
            WITH moved AS (
                DELETE FROM ONLY resource_asset WHERE kind_id = %(kind)s RETURNING *
            )
            INSERT INTO %(table)s SELECT * FROM moved
            """,
            kind=row[0],
            table=SQL.identifier(table),
        )
    )
    moved = cr.rowcount
    if moved:
        _debug.lifecycle("resource_asset.rows_moved", table=table, rows=moved)
        _logger.info(
            "resource_asset: moved %d %s row(s) into %s.", moved, kind_code, table
        )
    return moved
