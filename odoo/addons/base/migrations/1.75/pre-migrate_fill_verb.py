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
    ("_import_fill_invoice_line_taxes", "_import_add_invoice_line_taxes"),
    ("_import_invoice_fill_lines", "_import_invoice_add_lines"),
    (
        "_l10n_cl_fill_document_number_vals_from_xml",
        "_l10n_cl_add_document_number_vals_from_xml",
    ),
    ("_l10n_cl_fill_document_vals_from_xml", "_l10n_cl_add_document_vals_from_xml"),
    ("_l10n_cl_fill_lines_vals_from_xml", "_l10n_cl_add_lines_vals_from_xml"),
    ("_l10n_cl_fill_partner_vals_from_xml", "_l10n_cl_add_partner_vals_from_xml"),
    ("_l10n_cl_fill_references_vals_from_xml", "_l10n_cl_add_references_vals_from_xml"),
    (
        "_l10n_ec_edi_import_bill_fill_move_line",
        "_l10n_ec_edi_import_bill_add_move_line",
    ),
    ("_l10n_es_libros_fill_content", "_l10n_es_libros_write_content"),
    ("_l10n_es_libros_fill_header", "_l10n_es_libros_write_header"),
    (
        "_l10n_mx_edi_import_cfdi_fill_invoice",
        "_l10n_mx_edi_import_cfdi_update_invoice",
    ),
    (
        "_l10n_mx_edi_import_cfdi_fill_invoice_line",
        "_l10n_mx_edi_import_cfdi_update_invoice_line",
    ),
    (
        "_l10n_mx_edi_import_cfdi_fill_partner",
        "_l10n_mx_edi_import_cfdi_get_or_create_partner",
    ),
    ("_l10n_pl_fill_aggregate_values", "_l10n_pl_add_aggregate_values"),
    ("_l10n_pl_fill_move_values", "_l10n_pl_add_move_values"),
    ("_l10n_ro_saft_fill_account_code_by_id", "_l10n_ro_saft_add_account_code_by_id"),
    (
        "_l10n_ro_saft_fill_asset_transactions_values",
        "_l10n_ro_saft_add_asset_transactions_values",
    ),
    ("_l10n_ro_saft_fill_header_values", "_l10n_ro_saft_add_header_values"),
    ("_l10n_ro_saft_fill_invoice_values", "_l10n_ro_saft_add_invoice_values"),
    ("_l10n_ro_saft_fill_partner_values", "_l10n_ro_saft_add_partner_values"),
    ("_l10n_ro_saft_fill_payment_values", "_l10n_ro_saft_add_payment_values"),
    ("_l10n_ro_saft_fill_product_values", "_l10n_ro_saft_add_product_values"),
    (
        "_l10n_ro_saft_fill_report_assets_values",
        "_l10n_ro_saft_add_report_assets_values",
    ),
    ("_l10n_ro_saft_fill_tax_values", "_l10n_ro_saft_add_tax_values"),
    ("_l10n_ro_saft_fill_uom_values", "_l10n_ro_saft_add_uom_values"),
    (
        "_nemhandel_fill_participant_supported_documents",
        "_nemhandel_update_participant_supported_documents",
    ),
    (
        "_saft_fill_report_general_ledger_accounts",
        "_saft_add_report_general_ledger_accounts",
    ),
    (
        "_saft_fill_report_general_ledger_entries",
        "_saft_add_report_general_ledger_entries",
    ),
    (
        "_saft_fill_report_partner_ledger_values",
        "_saft_add_report_partner_ledger_values",
    ),
    ("_saft_fill_report_tax_details_values", "_saft_add_report_tax_details_values"),
    ("_slots_fill_resources_availability", "_slots_add_resources_availability"),
    ("_slots_fill_users_availability", "_slots_add_users_availability"),
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
                    "base 1.75: %s.%s %s -> %s (%d row(s))",
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
                "base 1.75: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
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
                        "base 1.75: %s.%s %s() -> %s() (%d row(s))",
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
