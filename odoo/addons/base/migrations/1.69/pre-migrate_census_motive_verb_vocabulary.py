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
    ("_checkout_invoice_info_form_validate", "_checkout_get_invoice_info_form_errors"),
    (
        "_documents_ensure_journal_folder_created",
        "_documents_get_or_create_journal_folders",
    ),
    ("_documents_ensure_journal_tags_created", "_documents_get_or_create_journal_tags"),
    ("_fsm_ensure_sale_order", "_fsm_get_or_create_sale_order"),
    ("_l10n_be_codabox_verify_prerequisites", "_l10n_be_codabox_check_prerequisites"),
    ("_l10n_ca_cpa005_pre_validate", "_l10n_ca_cpa005_check_prerequisites"),
    (
        "_l10n_co_dian_validate_send_event_update_data",
        "_l10n_co_dian_check_send_event_update_data",
    ),
    ("_l10n_eg_validate_info_address", "_l10n_eg_is_info_address_complete"),
    ("_l10n_in_validate_partner", "_l10n_in_get_partner_errors"),
    ("_l10n_in_validate_qr_data", "_l10n_in_is_qr_data_complete"),
    ("_l10n_jo_validate_config", "_l10n_jo_get_config_errors"),
    ("_l10n_jo_validate_fields", "_l10n_jo_get_field_errors"),
    ("_l10n_ke_validate_move", "_l10n_ke_get_move_errors"),
    ("_l10n_mx_edi_finkok_verify_is_stamped", "_l10n_mx_edi_finkok_is_stamped"),
    ("_l10n_ro_edi_stock_validate_carrier", "_l10n_ro_edi_stock_check_carrier"),
    (
        "_l10n_ro_edi_stock_validate_carrier_filter",
        "_l10n_ro_edi_stock_is_carrier_check_required",
    ),
    ("_l10n_ro_edi_stock_validate_data", "_l10n_ro_edi_stock_get_data_errors"),
    (
        "_l10n_ro_edi_stock_validate_fetch_data",
        "_l10n_ro_edi_stock_get_fetch_data_errors",
    ),
    (
        "_l10n_tr_nilvera_validate_partner_details",
        "_l10n_tr_nilvera_get_partner_detail_errors",
    ),
    ("_l10n_tr_validate_edispatch_fields", "_l10n_tr_get_edispatch_field_errors"),
    ("_l10n_tr_validate_edispatch_on_done", "_l10n_tr_get_edispatch_errors_on_done"),
    ("_l10n_uy_edi_validate_company_data", "_l10n_uy_edi_get_company_data_errors"),
    ("_post_validate", "_check_before_post"),
    ("_relation_ensure_indexes", "_relation_create_indexes"),
    ("_se_validate_bankgiro", "_se_is_bankgiro_valid"),
    ("_se_validate_bban", "_se_is_bban_valid"),
    ("_se_validate_domestic_account_format", "_se_is_domestic_account_format_valid"),
    ("_se_validate_plusgiro", "_se_is_plusgiro_valid"),
    ("_transfer_ensure_pending_msg_is_set", "_transfer_update_missing_pending_msg"),
    ("_ws_verify_request_data", "_ws_check_request_data"),
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
                    "base 1.69: %s.%s %s -> %s (%d row(s))",
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
                "base 1.69: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
