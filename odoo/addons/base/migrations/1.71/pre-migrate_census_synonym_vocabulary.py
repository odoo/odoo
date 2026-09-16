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
    ("_cron_delete_processed_transactions", "_cron_remove_processed_transactions"),
    ("_cron_delete_unused_connection", "_cron_remove_unused_connection"),
    ("_cron_l10n_ro_edi_synchronize_invoices", "_cron_l10n_ro_edi_sync_invoices"),
    ("_cron_purge_audio", "_cron_remove_audio"),
    ("_cron_synchronize_all_databases", "_cron_sync_all_databases"),
    (
        "_cron_synchronize_all_databases_with_odoocom",
        "_cron_sync_all_databases_with_odoocom",
    ),
    ("_dk_inject_report_into_xlsx_sheet", "_dk_write_report_into_xlsx_sheet"),
    ("_do_synchronize", "_do_sync"),
    ("_ee_inject_report_into_xlsx_sheet", "_ee_write_report_into_xlsx_sheet"),
    (
        "_es_libro_diario_inject_report_into_xlsx_sheet",
        "_es_libro_diario_write_report_into_xlsx_sheet",
    ),
    ("_facebook_comment_delete", "_facebook_remove_comment"),
    ("_instagram_comment_delete", "_instagram_remove_comment"),
    (
        "_l10n_mx_edi_cfdi_invoice_append_addendas",
        "_l10n_mx_edi_cfdi_invoice_add_addendas",
    ),
    ("_linkedin_comment_delete", "_linkedin_remove_comment"),
    ("_linkedin_delete_post", "_linkedin_remove_post"),
    ("_request_ciusro_synchronize_invoices", "_request_ciusro_sync_invoices"),
    ("_tds_tcs_inject_report_into_xlsx_sheet", "_tds_tcs_write_report_into_xlsx_sheet"),
    ("_twitter_tweet_delete", "_twitter_remove_tweet"),
    ("_youtube_comment_delete", "_youtube_remove_comment"),
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
                    "base 1.71: %s.%s %s -> %s (%d row(s))",
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
                "base 1.71: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
