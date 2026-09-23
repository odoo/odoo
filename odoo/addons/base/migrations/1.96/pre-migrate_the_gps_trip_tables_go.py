"""Two tables nothing can read any more, dropped at the user's instruction.

`remote_gps_trip` (469 rows on the production copy) and
`remote_gps_dashboard` (0) outlived the module that wrote them: no `ir_model`
row names either, nothing in the four repos defines the models, and the
device-family rename did not orphan them -- they are already orphaned in the
2026-09-13 dump, so they predate it.

1.70's rule stands: a migration deletes a model only when deleting it loses
nothing, and destroying data takes a person's decision and its own migration.
This is that migration, and the decision was taken on 2026-09-23. It is the
same shape as 1.73, with one difference: there is no `ir_model` row to remove
first, so what has to be proved is that nothing live claims the table.
"""

import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

TABLES = {
    "remote_gps_trip": "remote.gps.trip",
    "remote_gps_dashboard": "remote.gps.dashboard",
}


def migrate(cr, version):
    if not version:
        return
    for table, model in TABLES.items():
        cr.execute("SELECT to_regclass(%s)", [f"public.{table}"])
        [exists] = cr.fetchone()
        if exists is None:
            continue

        # a model of that name would make the table live again
        cr.execute("SELECT count(*) FROM ir_model WHERE model = %s", [model])
        [claimed] = cr.fetchone()
        # and so would a many2many whose relation it is
        cr.execute(
            "SELECT count(*) FROM ir_model_fields WHERE relation_table = %s", [table]
        )
        [related] = cr.fetchone()
        if claimed or related:
            _logger.warning(
                "%s is claimed (%s model row(s), %s relation field(s)) and is kept",
                table,
                claimed,
                related,
            )
            continue

        cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(table)))
        [rows] = cr.fetchone()
        cr.execute(SQL("DROP TABLE %s", SQL.identifier(table)))
        _logger.info(
            "dropped orphaned table %r with %s row(s), at the user's instruction: "
            "no model names it and no module on the addons path defines one",
            table,
            rows,
        )
