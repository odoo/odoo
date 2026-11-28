import logging

_logger = logging.getLogger(__name__)

_ORPHAN_SCHOOL_MANAGEMENT_XMLIDS = (
    "view_purchase_order_form_inherit_class_book",
    "view_university_class_section_form_inherit_book_purchase",
    "view_university_class_section_list_inherit_book_purchase",
    "view_university_subject_form_inherit_books",
    "view_university_enrollment_list_inherit_books",
    "action_university_class_section_missing_books",
    "menu_university_class_section_missing_books",
)

_MODEL_TABLES = {
    "ir.ui.view": "ir_ui_view",
    "ir.ui.menu": "ir_ui_menu",
    "ir.actions.act_window": "ir_act_window",
    "ir.actions.act_window.view": "ir_act_window_view",
}


def _cleanup_orphan_school_management_ui(cr):
    cr.execute(
        """
        SELECT model, res_id, name
        FROM ir_model_data
        WHERE module = 'school_management'
          AND name = ANY(%s)
        """,
        (list(_ORPHAN_SCHOOL_MANAGEMENT_XMLIDS),),
    )
    for model, res_id, name in cr.fetchall():
        table = _MODEL_TABLES.get(model) or model.replace(".", "_")
        cr.execute("SAVEPOINT school_purchase_orphan")
        try:
            # Menus reference actions; delete menu first when cleaning both.
            if model == "ir.actions.act_window":
                cr.execute(
                    "DELETE FROM ir_ui_menu WHERE action = %s",
                    ("ir.actions.act_window,%s" % res_id,),
                )
            cr.execute(f'DELETE FROM "{table}" WHERE id = %s', (res_id,))
            cr.execute(
                """
                DELETE FROM ir_model_data
                WHERE module = 'school_management' AND name = %s
                """,
                (name,),
            )
            cr.execute("RELEASE SAVEPOINT school_purchase_orphan")
            _logger.info("Removed orphan school_management.%s", name)
        except Exception as exc:  # noqa: BLE001
            cr.execute("ROLLBACK TO SAVEPOINT school_purchase_orphan")
            _logger.warning("Could not remove orphan school_management.%s: %s", name, exc)


def pre_init_hook(env):
    """Cleanup legacy school_management book UI on first install."""
    _cleanup_orphan_school_management_ui(env.cr)
