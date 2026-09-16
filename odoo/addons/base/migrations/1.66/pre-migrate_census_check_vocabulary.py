import logging

from odoo.db import schema

_logger = logging.getLogger(__name__)

_STORED_PYTHON = (
    ("ir_act_server", "code"),
    ("ir_actions_server_history", "code"),
    ("ir_model_fields", "compute"),
    ("hr_salary_rule", "amount_python_compute"),
    ("hr_salary_rule", "condition_python"),
)

_RENAMES = (
    ("_check_billing_address", "_is_billing_address_complete"),
    ("_check_delivery_address", "_is_delivery_address_complete"),
    ("_check_existing_payment", "_has_existing_payment"),
    ("_check_file_format", "_is_spreadsheet_file"),
    ("_check_for_sms_composer", "_can_use_sms_composer"),
    ("_check_message", "_get_message_errors"),
    ("_check_organizer_validation_conditions", "_get_organizer_validation_conditions"),
    ("_check_timesheet_can_be_billed", "_can_timesheet_be_billed"),
    ("_check_token", "_is_access_token_matching"),
    ("_check_values_to_sync", "_has_values_to_sync"),
    ("_check_warn_sms", "_get_pickings_to_warn_sms"),
    ("check_payments_for_warnings", "get_payment_warnings"),
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
                    "base 1.66: %s.%s %s -> %s (%d row(s))",
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
                "base 1.66: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
