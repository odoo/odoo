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

_RENDERED = (
    ("ir_ui_view", ("arch_db",)),
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

_CALL_WITH_ARGUMENTS = r"\s*\((?!\s*\))"

_CALL_RENAMES = (
    (
        r"\._compute_price\s*\((\s*(?:\\?[" + "'\"" + r"]|&quot;|&apos;|&#39;))",
        r"._get_prices(\1",
    ),
    (r"\._compute_price" + _CALL_WITH_ARGUMENTS, "._get_price_in_unit("),
    (r"\._compute_quantity" + _CALL_WITH_ARGUMENTS, "._get_quantity_in_unit("),
    (r"\._compute_base_price" + _CALL_WITH_ARGUMENTS, "._get_base_price("),
    (r"\._compute_reference" + _CALL_WITH_ARGUMENTS, "._get_unique_reference("),
    (r"\._compute_terms" + _CALL_WITH_ARGUMENTS, "._get_terms("),
    (r"\._compute_amount" + _CALL_WITH_ARGUMENTS, "._get_minimum_amount("),
    (r"\._compute_amounts" + _CALL_WITH_ARGUMENTS, "._prepare_closing_vals("),
    (r"\._compute_currency_id" + _CALL_WITH_ARGUMENTS, "._get_converted_price("),
    (r"\._compute_order_count" + _CALL_WITH_ARGUMENTS, "._update_order_count("),
    (r"\._compute_result" + _CALL_WITH_ARGUMENTS, "._get_grouped_result("),
    (r"\._compute_subtotal" + _CALL_WITH_ARGUMENTS, "._get_subtotal_from_total("),
    (r"\._compute_total_cost" + _CALL_WITH_ARGUMENTS, "._update_total_cost("),
    (r"\._compute_string_to_hash" + _CALL_WITH_ARGUMENTS, "._get_string_to_hash("),
)

_RENAMES_BY_MODEL = (
    ("_compute_statistics", "_update_statistics", "social.account"),
    ("_compute_website_url", "_get_forum_url", "forum.forum"),
    (
        "_compute_worksheet_template_id",
        "_update_worksheet_template_id",
        "product.template",
    ),
    (
        "_default_project_id",
        "_get_default_project_id",
        "helpdesk.ticket.convert.wizard",
    ),
    (
        "_default_team_id",
        "_get_default_helpdesk_team_id",
        "project.task.convert.wizard",
    ),
    ("_default_team_id", "_get_default_sale_team_id", "sale.order"),
    ("_default_question_ids", "_get_default_question_ids", "event.event"),
    ("_inverse_name", "_update_name_parts", "hr.employee"),
    ("_inverse_service_policy", "_update_service_policy_fields", "product.product"),
)


def _rewrite(cr, table, column, source, cast):
    for pattern, replacement in _CALL_RENAMES:
        cr.execute(
            f"UPDATE {table} SET {column} ="
            f" regexp_replace({source}, %(pat)s, %(new)s, 'g'){cast}"
            f" WHERE {source} ~ %(pat)s",
            {"pat": pattern, "new": replacement},
        )
        if cr.rowcount:
            _logger.info(
                "base 1.77: %s.%s %s -> %s (%d row(s))",
                table,
                column,
                pattern,
                replacement,
                cr.rowcount,
            )


def _rewrite_stored_python(cr):
    for table, column in _STORED_PYTHON:
        if not schema.table_exists(cr, table) or not schema.column_exists(
            cr, table, column
        ):
            continue
        _rewrite(cr, table, column, column, "")


def _rewrite_rendered(cr):
    for table, rendered in _RENDERED:
        if not schema.table_exists(cr, table):
            continue
        columns = schema.get_table_columns(cr, table)
        for column in rendered:
            if column not in columns:
                continue
            is_jsonb = columns[column]["udt_name"] == "jsonb"
            source = f"{column}::text" if is_jsonb else column
            _rewrite(cr, table, column, source, "::jsonb" if is_jsonb else "")


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_rendered(cr)
    for old, new, model in _RENAMES_BY_MODEL:
        rename_in_stored_expressions(cr, old, new, model=model)
