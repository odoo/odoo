import logging

_logger = logging.getLogger(__name__)

DISSOLVED = "stock_maintenance"
INTO = "resource_asset_stock"


def migrate(cr, version):
    cr.execute(
        "SELECT name, id, state FROM ir_module_module WHERE name = ANY(%s)",
        [[DISSOLVED, INTO]],
    )
    rows = {name: (module_id, state) for name, module_id, state in cr.fetchall()}
    if DISSOLVED not in rows:
        return
    dissolved_id, dissolved_state = rows[DISSOLVED]
    _drop_views(cr)
    into_id, into_state = rows.get(INTO, (None, "uninstalled"))
    if dissolved_state == "installed" and into_state == "uninstalled":
        if into_id:
            _delete_module_row(cr, into_id)
        _rename_module_row(cr, dissolved_id)
        _logger.info("%s became %s, which carries its location counts", DISSOLVED, INTO)
        return
    _merge_xmlids(cr)
    cr.execute(
        """
        DELETE FROM ir_module_module_dependency stale
              WHERE stale.name = %s
                AND EXISTS (SELECT 1 FROM ir_module_module_dependency kept
                             WHERE kept.module_id = stale.module_id AND kept.name = %s)
        """,
        [DISSOLVED, INTO],
    )
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
        [INTO, DISSOLVED],
    )
    _delete_module_row(cr, dissolved_id)
    _logger.info("dropped the %s module row, folded into %s", DISSOLVED, INTO)


def _drop_views(cr):
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
        [DISSOLVED],
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


def _merge_xmlids(cr):
    cr.execute(
        """
        DELETE FROM ir_model_data stale
              WHERE stale.module = %s
                AND EXISTS (SELECT 1 FROM ir_model_data kept
                             WHERE kept.module = %s AND kept.name = stale.name)
        """,
        [DISSOLVED, INTO],
    )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s", [INTO, DISSOLVED]
    )


def _rename_module_row(cr, module_id):
    cr.execute(
        "UPDATE ir_module_module SET name = %s, data_file_checksums = NULL WHERE id = %s",
        [INTO, module_id],
    )
    cr.execute(
        "UPDATE ir_module_module_dependency SET name = %s WHERE name = %s",
        [INTO, DISSOLVED],
    )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s", [INTO, DISSOLVED]
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s"
        " WHERE module = 'base' AND model = 'ir.module.module' AND name = %s",
        [f"module_{INTO}", f"module_{DISSOLVED}"],
    )


def _delete_module_row(cr, module_id):
    for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
        cr.execute(f"DELETE FROM {table} WHERE module_id = %s", [module_id])
    cr.execute(
        "DELETE FROM ir_model_data"
        " WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s",
        [module_id],
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", [module_id])
