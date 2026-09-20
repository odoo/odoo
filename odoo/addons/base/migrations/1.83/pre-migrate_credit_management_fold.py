import logging

_logger = logging.getLogger(__name__)

# credit_management 2.0 carries what its two satellites used to: the approval
# route of a credit verdict and the expected credit loss runs. A database that
# still has either module row would stop the loader on a module absent from
# disk, so their rows fold into the kernel before the graph is built.
DISSOLVED = ("credit_management_approval", "credit_management_provision")
INTO = "credit_management"


def migrate(cr, version):
    cr.execute(
        "SELECT name, id, state FROM ir_module_module WHERE name = ANY(%s)",
        [[*DISSOLVED, INTO]],
    )
    rows = {name: (module_id, state) for name, module_id, state in cr.fetchall()}
    if INTO not in rows:
        for name in DISSOLVED:
            if name in rows:
                _delete_module_row(cr, rows[name][0])
        return
    for name in DISSOLVED:
        if name not in rows:
            continue
        dissolved_id, _state = rows[name]
        _drop_views(cr, name)
        _merge_xmlids(cr, name)
        cr.execute(
            """
            DELETE FROM ir_module_module_dependency stale
                  WHERE stale.name = %s
                    AND EXISTS (SELECT 1 FROM ir_module_module_dependency kept
                                 WHERE kept.module_id = stale.module_id AND kept.name = %s)
            """,
            [name, INTO],
        )
        cr.execute(
            "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
            [INTO, name],
        )
        _delete_module_row(cr, dissolved_id)
        _logger.info("dropped the %s module row, folded into %s", name, INTO)
    cr.execute(
        "UPDATE ir_module_module SET state = 'to upgrade' WHERE name = %s AND state = 'installed'",
        [INTO],
    )


def _drop_views(cr, module):
    cr.execute(
        """
        WITH RECURSIVE doomed AS (
            SELECT res_id AS id FROM ir_model_data
             WHERE module = %s AND model = 'ir.ui.view'
             UNION
            SELECT view.id FROM ir_ui_view view JOIN doomed ON view.inherit_id = doomed.id
        )
        SELECT array_agg(id) FROM doomed
        """,
        [module],
    )
    view_ids = cr.fetchone()[0] or []
    if not view_ids:
        return
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id = ANY(%s)",
        [view_ids],
    )
    cr.execute(
        "UPDATE ir_ui_view SET inherit_id = NULL, mode = 'primary' WHERE id = ANY(%s)",
        [view_ids],
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id = ANY(%s)", [view_ids])


def _merge_xmlids(cr, module):
    cr.execute(
        """
        DELETE FROM ir_model_data stale
              WHERE stale.module = %s
                AND EXISTS (SELECT 1 FROM ir_model_data kept
                             WHERE kept.module = %s AND kept.name = stale.name)
        """,
        [module, INTO],
    )
    cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", [INTO, module])


def _delete_module_row(cr, module_id):
    for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
        cr.execute(f"DELETE FROM {table} WHERE module_id = %s", [module_id])
    cr.execute(
        "DELETE FROM ir_model_data"
        " WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s",
        [module_id],
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", [module_id])
