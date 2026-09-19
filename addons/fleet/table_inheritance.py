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

from odoo.addons.resource_asset.table_inheritance import move_rows_into_subtype_table

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
    return move_rows_into_subtype_table(cr, "vehicle", VEHICLE_TABLE)
