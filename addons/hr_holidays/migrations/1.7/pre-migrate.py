from odoo.db.schema import column_exists

OLD = "elligible_for_accrual_rate"
NEW = "eligible_for_accrual_rate"
TABLES = ("hr_leave_type", "resource_schedule_exception")
MODELS = ("hr.leave.type", "resource.schedule.exception")


def _rewrite(expr):
    return rf"regexp_replace({expr}, '\y{OLD}\y', '{NEW}', 'g')"


def _matches(expr):
    return rf"{expr} ~ '\y{OLD}\y'"


def migrate(cr, version):
    if not version:
        return

    for table in TABLES:
        if column_exists(cr, table, OLD) and not column_exists(cr, table, NEW):
            cr.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{OLD}" TO "{NEW}"')

    cr.execute(
        """
        UPDATE ir_model_fields SET name = %s
         WHERE name = %s AND model = ANY(%s)
        """,
        (NEW, OLD, list(MODELS)),
    )
    cr.execute(
        f"""
        UPDATE ir_ui_view
           SET arch_db = {_rewrite("arch_db::text")}::jsonb
         WHERE {_matches("arch_db::text")}
        """
    )
    cr.execute(
        f"""
        UPDATE ir_filters
           SET domain = {_rewrite("domain")},
               context = {_rewrite("context")},
               sort = {_rewrite("sort")}
         WHERE {_matches("domain")}
            OR {_matches("context")}
            OR {_matches("sort")}
        """
    )
    cr.execute(
        f"""
        UPDATE ir_act_window
           SET domain = {_rewrite("domain")},
               context = {_rewrite("context")}
         WHERE {_matches("domain")} OR {_matches("context")}
        """
    )
    cr.execute(
        f"""
        UPDATE ir_act_server
           SET code = {_rewrite("code")}
         WHERE {_matches("code")}
        """
    )
