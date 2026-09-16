import logging

from odoo.db import schema
from odoo.tools.module_data import rename_in_stored_expressions

_logger = logging.getLogger(__name__)

_STORED_PYTHON = (
    ("ir_act_server", "code"),
    ("ir_actions_server_history", "code"),
    ("ir_model_fields", "compute"),
    ("hr_salary_rule", "amount_python_compute"),
    ("hr_salary_rule", "condition_python"),
)

_RENAMES = (
    ("_compute_abc_classification", "_run_abc_classification"),
    ("_compute_account_id_on_product_lines", "_update_account_id_on_product_lines"),
    ("_compute_account_id_on_term_lines", "_update_account_id_on_term_lines"),
    ("_compute_amount_line_all", "_get_amount_line_all"),
    ("_compute_amount_total_without_delivery", "_get_amount_total_without_delivery"),
    ("_compute_approval_required_document", "_update_approval_required_document"),
    ("_compute_bacs_submission_serial", "_onchange_date"),
    ("_compute_criticality_classification", "_run_criticality_classification"),
    (
        "_compute_demand_variability_classification",
        "_run_demand_variability_classification",
    ),
    ("_compute_desired_approvers", "_get_desired_approvers"),
    ("_compute_inventory_aging_classification", "_run_inventory_aging_classification"),
    ("_compute_inventory_value_classification", "_run_inventory_value_classification"),
    ("_compute_kpi", "_update_kpi"),
    ("_compute_l10n_br_is_avatax_depends", "_get_fields_l10n_br_is_avatax_depends"),
    ("_compute_l10n_ch_declare_salary_data", "_update_l10n_ch_declare_salary_data"),
    ("_compute_payslip_properties", "_update_payslip_properties"),
    (
        "_compute_procurement_difficulty_classification",
        "_run_procurement_difficulty_classification",
    ),
    ("_compute_reconditioning_dates", "_update_reconditioning_dates"),
    ("_compute_sale_stock_classification", "_run_sale_stock_classification"),
    ("_compute_selected_groupby", "_get_selected_groupby"),
    ("_compute_slots_usage", "_get_slots_usage"),
    ("_compute_surface_from_geom", "_update_surface_from_geom"),
    ("_compute_worked_days_ytd", "_update_worked_days_ytd"),
    ("_default_activity_type", "_get_default_activity_type"),
    ("_default_company_token", "_get_new_attendance_kiosk_key"),
    (
        "_default_discount_value_on_module_install",
        "_update_discount_product_on_module_install",
    ),
    ("_default_end_datetime", "_get_default_end_datetime"),
    ("_default_event_mail_ids", "_get_default_event_mail_ids"),
    ("_default_feed_is_valid", "_is_default_feed_valid"),
    (
        "_default_settle_deposit_product_on_module_install",
        "_update_settle_deposit_products_on_module_install",
    ),
    ("_default_stage_ids", "_get_or_create_default_stages"),
    ("_default_start_datetime", "_get_default_start_datetime"),
    ("_default_website_meta", "_get_default_website_meta"),
)

_RENAMES_BY_MODEL = (
    ("_default_user", "_get_default_user_id", "account.analytic.line"),
)

_RENDERED_TEMPLATES = (
    (
        "mail_template",
        (
            "subject",
            "body_html",
            "email_from",
            "email_to",
            "email_cc",
            "reply_to",
            "partner_to",
            "scheduled_date",
        ),
    ),
    ("sms_template", ("body",)),
)


def _pattern(name):
    return r"\." + name + r"\M"


def _call_pattern(name):
    return r"\." + name + r"\("


def _rewrite_stored_python(cr):
    for table, column in _STORED_PYTHON:
        if not schema.table_exists(cr, table) or not schema.column_exists(
            cr, table, column
        ):
            continue
        for old, new in _RENAMES:
            cr.execute(
                f"UPDATE {table} SET {column} ="
                f" regexp_replace({column}, %(pat)s, %(new)s, 'g')"
                f" WHERE {column} ~ %(pat)s",
                {"pat": _pattern(old), "new": "." + new},
            )
            if cr.rowcount:
                _logger.info(
                    "base 1.76: %s.%s %s -> %s (%d row(s))",
                    table,
                    column,
                    old,
                    new,
                    cr.rowcount,
                )


def _rewrite_view_calls(cr):
    columns = schema.get_table_columns(cr, "ir_ui_view")
    if "arch_db" not in columns:
        return
    is_jsonb = columns["arch_db"]["udt_name"] == "jsonb"
    source = "arch_db::text" if is_jsonb else "arch_db"
    cast = "::jsonb" if is_jsonb else ""
    for old, new in _RENAMES:
        cr.execute(
            f"UPDATE ir_ui_view SET arch_db ="
            f" regexp_replace({source}, %(pat)s, %(new)s, 'g'){cast}"
            f" WHERE {source} ~ %(pat)s",
            {"pat": _call_pattern(old), "new": "." + new + "("},
        )
        if cr.rowcount:
            _logger.info(
                "base 1.76: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def _rewrite_template_calls(cr):
    for table, rendered in _RENDERED_TEMPLATES:
        if not schema.table_exists(cr, table):
            continue
        columns = schema.get_table_columns(cr, table)
        for column in rendered:
            if column not in columns:
                continue
            is_jsonb = columns[column]["udt_name"] == "jsonb"
            source = f"{column}::text" if is_jsonb else column
            cast = "::jsonb" if is_jsonb else ""
            for old, new in _RENAMES:
                cr.execute(
                    f"UPDATE {table} SET {column} ="
                    f" regexp_replace({source}, %(pat)s, %(new)s, 'g'){cast}"
                    f" WHERE {source} ~ %(pat)s",
                    {"pat": _call_pattern(old), "new": "." + new + "("},
                )
                if cr.rowcount:
                    _logger.info(
                        "base 1.76: %s.%s %s() -> %s() (%d row(s))",
                        table,
                        column,
                        old,
                        new,
                        cr.rowcount,
                    )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
    _rewrite_template_calls(cr)
    for old, new, model in _RENAMES_BY_MODEL:
        rename_in_stored_expressions(cr, old, new, model=model)
