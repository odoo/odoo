"""The vehicle table, which the ORM does not create.

A table that inherits another is written by hand -- `base/data/base_data.sql`
does the same for `ir_act_window` and its siblings -- because the schema pass
only knows how to make an ordinary one. It has to exist before that pass runs,
which is `pre_init_hook` on an install and the pre-migration on an upgrade.
"""

import logging

from odoo.db.schema import column_exists, table_exists
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


def name_the_vehicle_model(cr) -> None:
    if not column_exists(cr, "resource_asset_kind", "model_name"):
        _debug.logic("fleet.vehicle_model.not_nameable_yet")
        _logger.info(
            "fleet: resource_asset_kind.model_name is not there yet; upgrade "
            "resource_asset in the same run for the vehicle kind to name its model."
        )
        return
    cr.execute(
        "UPDATE resource_asset_kind SET model_name = %s WHERE code = 'vehicle'",
        ["resource.asset.vehicle"],
    )


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
