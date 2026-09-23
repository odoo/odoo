import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

ABSORBED = "stock_blocked_location"
ABSORBER = "stock"

DROPPED_VIEWS = (
    "view_stock_location_search_blocked",
    "view_stock_location_tree_blocked",
    "view_stock_location_form_blocked",
)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return
    if not _is_installed(cr):
        return
    _drop_inherited_views(cr)
    _rehome_model_data(cr)
    _rehome_reflection(cr)
    _drop_module(cr)


def _is_installed(cr: Cursor) -> bool:
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = %s", (ABSORBED,))
    return bool(cr.fetchone())


def _drop_inherited_views(cr: Cursor) -> None:
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (SELECT res_id FROM ir_model_data
                       WHERE module = %s AND model = 'ir.ui.view'
                         AND name = ANY(%s))
        """,
        (ABSORBED, list(DROPPED_VIEWS)),
    )
    dropped = cr.rowcount
    cr.execute(
        "DELETE FROM ir_model_data"
        " WHERE module = %s AND model = 'ir.ui.view' AND name = ANY(%s)",
        (ABSORBED, list(DROPPED_VIEWS)),
    )
    _logger.info("stock_blocked_location: dropped %d inherited view(s)", dropped)


def _rehome_model_data(cr: Cursor) -> None:
    cr.execute(
        """
        DELETE FROM ir_model_data d
         WHERE d.module = %s
           AND EXISTS (SELECT 1 FROM ir_model_data o
                        WHERE o.module = %s AND o.name = d.name)
        """,
        (ABSORBED, ABSORBER),
    )
    cr.execute(
        "UPDATE ir_model_data SET module = %s WHERE module = %s",
        (ABSORBER, ABSORBED),
    )
    _logger.info("stock_blocked_location: re-homed %d xml id(s) to stock", cr.rowcount)


def _rehome_reflection(cr: Cursor) -> None:
    for table, unique_by in (
        ("ir_model_constraint", "name"),
        ("ir_model_relation", "name"),
    ):
        cr.execute(
            f"""
            DELETE FROM {table} r
             USING ir_module_module absorbed, ir_module_module absorber
             WHERE r.module = absorbed.id
               AND absorbed.name = %s AND absorber.name = %s
               AND EXISTS (SELECT 1 FROM {table} o
                            WHERE o.module = absorber.id
                              AND o.{unique_by} = r.{unique_by})
            """,
            (ABSORBED, ABSORBER),
        )
        cr.execute(
            f"""
            UPDATE {table} r
               SET module = absorber.id
              FROM ir_module_module absorbed, ir_module_module absorber
             WHERE r.module = absorbed.id
               AND absorbed.name = %s AND absorber.name = %s
            """,
            (ABSORBED, ABSORBER),
        )


def _drop_module(cr: Cursor) -> None:
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name = %s", (ABSORBED,))
    cr.execute("DELETE FROM ir_module_module_exclusion WHERE name = %s", (ABSORBED,))
    cr.execute(
        "DELETE FROM ir_model_data"
        " WHERE module = 'base' AND model = 'ir.module.module' AND name = %s",
        (f"module_{ABSORBED}",),
    )
    cr.execute("DELETE FROM ir_module_module WHERE name = %s", (ABSORBED,))
    _logger.info("stock_blocked_location: module row removed, absorbed into stock")
