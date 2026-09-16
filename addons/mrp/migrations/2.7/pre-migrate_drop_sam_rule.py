"""Drop `stock.warehouse.sam_rule_id`, which nothing ever wrote.

The three-step manufacturing route ("pick components, manufacture, then store
products") builds its stock-after-manufacturing rule through the generic
`_prepare_rule_routings` / `pbm_route_id` machinery, which hangs the rule off
the route. The dedicated pointer was never assigned and never read, in this
repository or in enterprise, agromarin or design-themes -- so the column holds
NULL on every row of every database and only the schema remembers it.
"""

import logging

from odoo.libs.sql import SQL

_logger = logging.getLogger(__name__)

TABLE = "stock_warehouse"
COLUMN = "sam_rule_id"


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        SQL(
            "SELECT count(*) FROM %s WHERE %s IS NOT NULL",
            SQL.identifier(TABLE),
            SQL.identifier(COLUMN),
        )
    )
    [[populated]] = cr.fetchall()
    if populated:
        _logger.warning(
            "%s.%s holds %s non-NULL value(s); leaving the column in place"
            " rather than dropping data nothing is known to have written.",
            TABLE,
            COLUMN,
            populated,
        )
        return
    cr.execute(
        SQL(
            "ALTER TABLE %s DROP COLUMN IF EXISTS %s",
            SQL.identifier(TABLE),
            SQL.identifier(COLUMN),
        )
    )
