"""The vehicle table, created before the schema pass would.

The ORM creates a table that inherits another from `_table_inheritance_root`,
but only at the schema pass, and the rows of vehicle kind have to move out of
`resource_asset` before that pass reads them -- which is `pre_init_hook` on an
install and the pre-migration on an upgrade. So the table is made here, early,
and the schema pass finds it in place.
"""

import logging

from odoo.db.schema import table_exists
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

VEHICLE_TABLE = "resource_asset_vehicle"


def create_vehicle_table(cr) -> bool:
    if not table_exists(cr, "resource_asset") or table_exists(cr, VEHICLE_TABLE):
        _debug.logic("fleet.vehicle_table.skipped", table=VEHICLE_TABLE)
        return False
    cr.execute(
        SQL(
            "CREATE TABLE %s (PRIMARY KEY(id)) INHERITS (resource_asset)",
            SQL.identifier(VEHICLE_TABLE),
        )
    )
    _debug.lifecycle("fleet.vehicle_table.created", table=VEHICLE_TABLE)
    _logger.info("fleet: created %s inheriting resource_asset.", VEHICLE_TABLE)
    return True


def move_vehicles_into_their_table(cr) -> int:
    """Parent to child is a DELETE and an INSERT, because PostgreSQL moves no
    row between them. An id survives it only because the whole tree shares one
    sequence, and the DELETE is possible only because `resource_asset` 1.4
    dropped the foreign keys that would have refused it."""
    if not table_exists(cr, VEHICLE_TABLE):
        return 0
    cr.execute("SELECT id FROM resource_asset_kind WHERE code = 'vehicle'")
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
            table=SQL.identifier(VEHICLE_TABLE),
        )
    )
    moved = cr.rowcount
    if moved:
        _debug.lifecycle(
            "fleet.vehicles_moved", table=VEHICLE_TABLE, rows=moved
        )
        _logger.info("fleet: moved %d vehicle(s) into %s.", moved, VEHICLE_TABLE)
    return moved
