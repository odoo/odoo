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
}


def migrate(cr, version):
    """Remove orphaned school_management book-purchase UI that blocks view validation."""
    # Delete menus before actions they reference.
    ordered_names = (
        "menu_university_class_section_missing_books",
        "action_university_class_section_missing_books",
        "view_purchase_order_form_inherit_class_book",
        "view_university_class_section_form_inherit_book_purchase",
        "view_university_class_section_list_inherit_book_purchase",
        "view_university_subject_form_inherit_books",
        "view_university_enrollment_list_inherit_books",
    )
    for name in ordered_names:
        cr.execute(
            """
            SELECT model, res_id
            FROM ir_model_data
            WHERE module = 'school_management' AND name = %s
            """,
            (name,),
        )
        row = cr.fetchone()
        if not row:
            continue
        model, res_id = row
        table = _MODEL_TABLES.get(model) or model.replace(".", "_")
        cr.execute("SAVEPOINT school_purchase_orphan")
        try:
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
