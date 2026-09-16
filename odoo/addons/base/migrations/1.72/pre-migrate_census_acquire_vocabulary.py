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
    ("_cron_fetch_image", "_cron_update_images"),
    ("_cron_fetch_online_transactions", "_cron_import_online_transactions"),
    ("_cron_fetch_titles", "_cron_update_titles"),
    (
        "_cron_fetch_waiting_online_transactions",
        "_cron_import_waiting_online_transactions",
    ),
    ("_cron_l10n_ke_oscu_fetch_purchases", "_cron_l10n_ke_oscu_import_purchases"),
    ("_cron_starshipit_fetch_and_update_prices", "_cron_starshipit_update_prices"),
    ("_eh_payroll_cron_fetch_payrun", "_eh_payroll_cron_import_payrun"),
    ("_eh_payroll_fetch_journal_entries", "_eh_payroll_import_journal_entries"),
    ("_eh_payroll_fetch_payrun", "_eh_payroll_import_payrun"),
    ("_facebook_comment_fetch", "_facebook_get_comments"),
    ("_instagram_comment_fetch", "_instagram_get_comments"),
    ("_l10n_ae_faf_fetch_data", "_l10n_ae_faf_get_data"),
    (
        "_l10n_be_codabox_cron_fetch_coda_transactions",
        "_l10n_be_codabox_cron_import_coda_transactions",
    ),
    (
        "_l10n_be_codabox_cron_fetch_soda_transactions",
        "_l10n_be_codabox_cron_import_soda_transactions",
    ),
    (
        "_l10n_be_codabox_fetch_coda_transactions",
        "_l10n_be_codabox_import_coda_transactions",
    ),
    (
        "_l10n_be_codabox_fetch_soda_transactions",
        "_l10n_be_codabox_import_soda_transactions",
    ),
    (
        "_l10n_be_codabox_fetch_transactions_from_iap",
        "_l10n_be_codabox_download_transactions_from_iap",
    ),
    (
        "_l10n_be_codaclean_cron_fetch_coda_transactions",
        "_l10n_be_codaclean_cron_import_coda_transactions",
    ),
    ("_l10n_be_codaclean_fetch_coda_files", "_l10n_be_codaclean_download_coda_files"),
    (
        "_l10n_be_codaclean_fetch_coda_transactions",
        "_l10n_be_codaclean_download_coda_transactions",
    ),
    (
        "_l10n_be_fetch_document_from_myminfin",
        "_l10n_be_download_document_from_myminfin",
    ),
    (
        "_l10n_hr_mer_fetch_document_status_company",
        "_l10n_hr_mer_update_document_status_company",
    ),
    ("_l10n_id_qris_fetch_status", "_l10n_id_qris_get_status"),
    ("_l10n_ke_oscu_fetch_invoice_details", "_l10n_ke_oscu_get_invoice_details"),
    ("_l10n_ke_oscu_fetch_purchases", "_l10n_ke_oscu_import_purchases"),
    (
        "_l10n_pl_edi_try_status_fetch_from_ksef",
        "_l10n_pl_edi_try_update_status_from_ksef",
    ),
    (
        "_l10n_ro_edi_fetch_invoice_sent_documents",
        "_l10n_ro_edi_update_invoice_sent_documents",
    ),
    ("_l10n_ro_edi_fetch_invoices", "_l10n_ro_edi_import_invoices"),
    (
        "_l10n_ro_edi_stock_fetch_document_status",
        "_l10n_ro_edi_stock_update_document_status",
    ),
    ("_l10n_vn_edi_fetch_invoice_file_data", "_l10n_vn_edi_download_invoice_file_data"),
    (
        "_l10n_vn_edi_fetch_invoice_pdf_file_data",
        "_l10n_vn_edi_download_invoice_pdf_file_data",
    ),
    (
        "_l10n_vn_edi_fetch_invoice_xml_file_data",
        "_l10n_vn_edi_download_invoice_xml_file_data",
    ),
    (
        "_l10n_vn_edi_try_fetch_invoice_file_data",
        "_l10n_vn_edi_try_download_invoice_file_data",
    ),
    ("_linkedin_comment_fetch", "_linkedin_get_comments"),
    ("_linkedin_fetch_followers_count", "_linkedin_get_followers_count"),
    ("_mercado_pago_fetch_access_token", "_mercado_pago_get_access_token"),
    ("_paymob_fetch_access_token", "_paymob_get_access_token"),
    ("_paypal_fetch_access_token", "_paypal_get_access_token"),
    ("_request_ciusro_fetch_status", "_request_ciusro_get_status"),
    (
        "_stripe_fetch_or_create_connected_account",
        "_stripe_get_or_create_connected_account",
    ),
    ("_trigger_fetch_images_cron", "_trigger_update_images_cron"),
    ("_twitter_comment_fetch", "_twitter_get_comments"),
    ("_youtube_comment_fetch", "_youtube_get_comments"),
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
                    "base 1.72: %s.%s %s -> %s (%d row(s))",
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
                "base 1.72: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
