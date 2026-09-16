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
    ("_equity_ensure_token", "_equity_get_or_create_token"),
    ("_portal_ensure_token", "_portal_get_or_create_token"),
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
                    "base 1.74: %s.%s %s -> %s (%d row(s))",
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
                "base 1.74: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
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
                        "base 1.74: %s.%s %s() -> %s() (%d row(s))",
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
