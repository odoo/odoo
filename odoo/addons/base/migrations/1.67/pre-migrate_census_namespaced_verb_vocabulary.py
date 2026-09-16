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
    ("_ar_vat_line_build_query", "_ar_vat_line_get_query"),
    ("_dian_calculate_cude_sha384", "_dian_get_cude_sha384"),
    ("_import_create_or_retrieve_partner", "_import_get_or_create_partner"),
    (
        "_l10n_au_calculate_annual_leave_withholding",
        "_l10n_au_get_annual_leave_withholding",
    ),
    (
        "_l10n_au_calculate_long_service_leave_withholding",
        "_l10n_au_get_long_service_leave_withholding",
    ),
    ("_l10n_au_calculate_marginal_withhold", "_l10n_au_get_marginal_withhold"),
    (
        "_l10n_br_calculate_access_key_check_digit",
        "_l10n_br_get_access_key_check_digit",
    ),
    ("_l10n_co_dian_build_zip_attachment", "_l10n_co_dian_create_zip_attachment"),
    ("_l10n_in_retrieve_details_from_irn", "_l10n_in_get_details_from_irn"),
    ("_l10n_jo_build_jofotara_headers", "_l10n_jo_prepare_jofotara_headers"),
    (
        "_l10n_mx_edi_cfdi_build_document_values",
        "_l10n_mx_edi_cfdi_prepare_document_values",
    ),
    (
        "_l10n_sa_calculate_signed_properties_hash",
        "_l10n_sa_get_signed_properties_hash",
    ),
    ("_l10n_tr_build_document_uuids_list", "_l10n_tr_get_document_uuids"),
    ("_l10n_tr_calculate_net_guess_accuracy", "_l10n_tr_get_net_guess_accuracy"),
    ("_l10n_tw_edi_determine_tax_types", "_l10n_tw_edi_get_tax_types"),
    ("_l10n_uy_build_vat_error_message", "_l10n_uy_get_vat_error_message"),
    ("_l10n_vn_edi_lookup_invoice", "_l10n_vn_edi_get_invoice"),
    ("_nemhandel_lookup_participant", "_nemhandel_get_participant"),
    ("_peppol_lookup_participant", "_peppol_get_participant"),
    ("_stripe_calculate_amount", "_stripe_get_amount"),
    ("_timesheet_determine_sale_line", "_timesheet_get_sale_line"),
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
                    "base 1.67: %s.%s %s -> %s (%d row(s))",
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
                "base 1.67: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
