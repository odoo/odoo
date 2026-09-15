"""Pre-migration: `maintenance` absorbs `resource_asset_maintenance`.

A maintenance order now maintains resources, and `maintenance` depends on
`resource_asset`, so the bridge between them is empty. Its module row has to go
before the graph is assembled, because the loader stops on an installed module
absent from disk.

The bridge's field xml ids move to `maintenance` rather than staying behind:
`_process_end` deletes the record behind an orphaned `ir.model.fields` xml id. Its
order and plan views are dropped, because they name `asset_id`, which
`maintenance` no longer defines, and would fail validation when `maintenance`
reloads the views they inherit. The asset form view keeps its xml id, which
`maintenance` ships under the same name.
"""

import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

DISSOLVED = "resource_asset_maintenance"
INTO = "maintenance"
SUPERSEDED_VIEWS = (
    "maintenance_order_view_form_asset",
    "maintenance_plan_view_form_asset",
    "maintenance_plan_view_list_asset",
    "maintenance_order_view_search_asset",
)


def migrate(cr, version):
    cr.execute(
        "SELECT name, id FROM ir_module_module WHERE name = ANY(%s)",
        ([DISSOLVED, INTO],),
    )
    module_ids = dict(cr.fetchall())
    if DISSOLVED not in module_ids:
        return
    dissolved_id = module_ids[DISSOLVED]
    if INTO in module_ids:
        _drop_superseded_views(cr)
        _repoint_xmlids(cr)
        _move_schema_rows(cr, dissolved_id, module_ids[INTO])
        cr.execute(
            """
            DELETE FROM ir_module_module_dependency d
                  WHERE d.name = %s
                    AND EXISTS (SELECT 1
                                  FROM ir_module_module_dependency o
                                 WHERE o.module_id = d.module_id AND o.name = %s)
            """,
            (DISSOLVED, INTO),
        )
        cr.execute(
            "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
            (INTO, DISSOLVED),
        )
    cr.execute(
        "DELETE FROM ir_module_module_dependency WHERE module_id = %s",
        (dissolved_id,),
    )
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s",
        (dissolved_id,),
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", (dissolved_id,))
    _logger.info("dropped the %s module row, folded into %s", DISSOLVED, INTO)


def _drop_superseded_views(cr):
    names = list(SUPERSEDED_VIEWS)
    cr.execute(
        """
        UPDATE ir_ui_view child
           SET inherit_id = superseded.inherit_id
          FROM ir_ui_view superseded
          JOIN ir_model_data d ON d.res_id = superseded.id
         WHERE d.module = %s AND d.model = 'ir.ui.view' AND d.name = ANY(%s)
           AND child.inherit_id = superseded.id
        """,
        (DISSOLVED, names),
    )
    cr.execute(
        """
        DELETE FROM ir_ui_view
              WHERE id IN (SELECT res_id
                             FROM ir_model_data
                            WHERE module = %s AND model = 'ir.ui.view'
                              AND name = ANY(%s))
        """,
        (DISSOLVED, names),
    )
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)",
        (DISSOLVED, names),
    )


def _repoint_xmlids(cr):
    cr.execute(
        """
        DELETE FROM ir_model_data d
              WHERE d.module = %s
                AND EXISTS (SELECT 1
                              FROM ir_model_data o
                             WHERE o.module = %s
                               AND o.name = d.name
                               AND o.model = d.model
                               AND o.res_id = d.res_id)
        """,
        (DISSOLVED, INTO),
    )
    cr.execute(
        """
        SELECT d.name FROM ir_model_data d
         WHERE d.module = %s
           AND EXISTS (SELECT 1 FROM ir_model_data o
                        WHERE o.module = %s AND o.name = d.name)
        """,
        (DISSOLVED, INTO),
    )
    clashing = sorted(name for (name,) in cr.fetchall())
    if clashing:
        raise ValueError(
            f"{DISSOLVED} and {INTO} both own {clashing}, naming different records"
        )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s", (INTO, DISSOLVED)
    )
    _logger.info("repointed %s xml id(s) from %s to %s", cr.rowcount, DISSOLVED, INTO)


def _move_schema_rows(cr, from_id, to_id):
    for table in ("ir_model_constraint", "ir_model_relation"):
        cr.execute(
            SQL(
                """
                DELETE FROM %(table)s d
                      WHERE d.module = %(from_id)s
                        AND EXISTS (SELECT 1 FROM %(table)s o
                                     WHERE o.module = %(to_id)s AND o.name = d.name)
                """,
                table=SQL.identifier(table),
                from_id=from_id,
                to_id=to_id,
            )
        )
        cr.execute(
            SQL(
                "UPDATE %(table)s SET module = %(to_id)s WHERE module = %(from_id)s",
                table=SQL.identifier(table),
                from_id=from_id,
                to_id=to_id,
            )
        )
