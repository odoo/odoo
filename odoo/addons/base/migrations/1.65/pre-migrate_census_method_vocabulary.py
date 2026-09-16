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
    ("_cfdi_sanitize_to_legal_name", "_cfdi_normalize_legal_name"),
    ("_check_alias_name_is_sanitized", "_check_alias_name_is_normalized"),
    ("_check_camt", "_get_camt_root"),
    ("_check_coda", "_is_coda"),
    ("_check_currency_table_monocurrency", "_is_currency_table_monocurrency"),
    ("_check_date_segment", "_is_valid_date_segment"),
    ("_check_debit_credit_tags", "_has_matching_debit_credit_tags"),
    ("_check_edi_line_tax_required", "_is_edi_line_tax_required"),
    ("_check_employees_availability_for_event", "_get_unavailable_partners_for_event"),
    ("_check_execute_now_by_point", "_get_execute_now_by_point"),
    ("_check_is_certified_pos", "_is_certified_pos"),
    ("_check_ofx", "_is_ofx"),
    ("_check_old_event_update_required", "_is_old_event_update_required"),
    ("_check_overlapping_targets", "_get_overlapping_target_partner_names"),
    ("_check_pending_odoo_records", "_has_pending_odoo_records"),
    ("_check_qc_status", "_is_quality_check_done"),
    ("_check_qif", "_is_qif"),
    ("_check_rating_feature_enabled", "_is_rating_feature_enabled"),
    ("_check_sale_timesheet_feature_enabled", "_is_sale_timesheet_feature_enabled"),
    ("_check_sequence_gap_around", "_has_sequence_gap_around"),
    ("_check_sla_feature_enabled", "_is_sla_feature_enabled"),
    ("_check_sum", "_is_valuation_balanced"),
    ("_check_time_limit_exceeded", "_is_time_limit_exceeded"),
    (
        "_check_use_website_helpdesk_livechat_feature_enabled",
        "_is_website_helpdesk_livechat_feature_enabled",
    ),
    ("_check_zengin", "_is_zengin"),
    ("_compute_account_id_fallback", "_update_account_id_fallback"),
    ("_compute_accuracy_metrics", "_get_accuracy_metrics"),
    ("_compute_all_special_mode", "_get_all_special_mode"),
    ("_compute_all_tax_values", "_get_all_tax_values"),
    ("_compute_balances", "_get_balances"),
    ("_compute_board_amount", "_get_board_amount"),
    ("_compute_bom_price", "_get_bom_price"),
    ("_compute_chained_base_prices", "_get_chained_base_prices"),
    ("_compute_column_percent_comparison_data", "_get_column_percent_comparison_data"),
    ("_compute_combo_price", "_update_combo_price"),
    ("_compute_cost_sums", "_get_cost_sums"),
    ("_compute_current_production_capacity", "_get_current_production_capacity"),
    ("_compute_data_quality", "_get_data_quality"),
    ("_compute_delay_price", "_get_delay_price"),
    ("_compute_device_connection", "_get_device_connection"),
    ("_compute_duration_vals", "_get_duration_vals"),
    ("_compute_etag", "_get_etag"),
    ("_compute_formula_batch", "_get_formula_batch"),
    (
        "_compute_formula_batch_with_engine_account_codes",
        "_get_formula_batch_with_engine_account_codes",
    ),
    (
        "_compute_formula_batch_with_engine_custom",
        "_get_formula_batch_with_engine_custom",
    ),
    (
        "_compute_formula_batch_with_engine_domain",
        "_get_formula_batch_with_engine_domain",
    ),
    (
        "_compute_formula_batch_with_engine_external",
        "_get_formula_batch_with_engine_external",
    ),
    (
        "_compute_formula_batch_with_engine_tax_tags",
        "_get_formula_batch_with_engine_tax_tags",
    ),
    ("_compute_functions", "_get_functions"),
    ("_compute_goods_received_not_invoiced", "_get_goods_received_not_invoiced"),
    ("_compute_hash", "_get_hash"),
    ("_compute_invoice_amounts_single", "_update_invoice_amounts_single"),
    ("_compute_journal_balances", "_get_journal_balances"),
    ("_compute_liquidity_balance", "_get_liquidity_balance"),
    ("_compute_meeting", "_get_meetings_by_partner"),
    ("_compute_new_allocation", "_get_new_allocation"),
    ("_compute_presence_prorated_fixed_wage", "_get_presence_prorated_fixed_wage"),
    ("_compute_price_before_discount", "_get_price_before_discount"),
    ("_compute_price_estimate", "_get_price_estimate"),
    ("_compute_price_lenient", "_get_price_lenient"),
    ("_compute_price_report", "_get_price_report"),
    ("_compute_price_rule", "_get_price_rule"),
    ("_compute_price_rule_multi", "_get_price_rule_multi"),
    ("_compute_qrr_number", "_get_qrr_number"),
    ("_compute_quantity_estimate", "_get_quantity_estimate"),
    ("_compute_quantity_lenient", "_get_quantity_lenient"),
    ("_compute_quantity_reconcile", "_get_quantity_reconcile"),
    ("_compute_quantity_report", "_get_quantity_report"),
    ("_compute_quantity_stored", "_get_quantity_stored"),
    ("_compute_quiz_info", "_get_quiz_info"),
    ("_compute_reference_prefix", "_get_reference_prefix"),
    ("_compute_return_boxes", "_get_return_boxes"),
    ("_compute_sale_order_reference", "_get_sale_order_reference"),
    ("_compute_seasonal_metrics", "_get_seasonal_metrics"),
    ("_compute_show_tokenize_input_mapping", "_get_show_tokenize_input_mapping"),
    ("_compute_statistics_facebook_360d", "_get_statistics_facebook_360d"),
    ("_compute_statistics_instagram", "_get_statistics_instagram"),
    ("_compute_statistics_instagram_360d", "_get_statistics_instagram_360d"),
    ("_compute_statistics_linkedin", "_get_statistics_linkedin"),
    ("_compute_tax_closing_entry", "_get_tax_closing_entry"),
    ("_compute_totals_no_batch_aggregation", "_get_totals_no_batch_aggregation"),
    ("_compute_trail_analytics", "_get_trail_analytics"),
    ("_compute_treasury_timeframes", "_get_treasury_timeframes"),
    ("_compute_xml_version", "_get_xml_version"),
    ("_default_addressbook_specs", "_get_addressbook_specs"),
    ("_default_base_dir", "_get_base_dir"),
    ("_default_get_request_dates", "_get_get_request_dates"),
    ("_default_group_expand", "_get_group_expand"),
    ("_default_line_vals", "_get_line_vals"),
    ("_default_order_line_values", "_get_order_line_values"),
    ("_default_partner_field_name", "_get_partner_field_name"),
    ("_default_repartition_lines", "_get_repartition_lines"),
    ("_default_subtypes", "_get_subtypes"),
    ("_default_user_calendar_default_privacy", "_get_user_calendar_default_privacy"),
    ("_default_user_field_name", "_get_user_field_name"),
    ("_default_wizard_line_vals", "_get_wizard_line_vals"),
    ("_get_default_subtypes", "_get_get_subtypes"),
    ("_get_id_number_sanitize", "_get_id_number_digits"),
    ("_prepare_default_order_line_values", "_prepare_get_order_line_values"),
    ("_sanitize_alias_domain_name", "_normalize_alias_domain_name"),
    ("_sanitize_alias_name", "_normalize_alias_name"),
    ("_sanitize_allowed_domains", "_normalize_allowed_domains"),
    ("_sanitize_applied_on_vals", "_update_applied_on_vals"),
    ("_sanitize_client_address_params", "_filter_client_address_params"),
    ("_sanitize_command_token", "_normalize_command_token"),
    ("_sanitize_configuration", "_update_configuration"),
    ("_sanitize_cookies", "_update_cookies"),
    ("_sanitize_ean", "_normalize_ean"),
    ("_sanitize_export_cell", "_escape_export_cell"),
    ("_sanitize_fetch_params", "_filter_fetch_params"),
    ("_sanitize_file_extension", "_normalize_file_extension"),
    ("_sanitize_html_columns", "_update_html_columns"),
    ("_sanitize_ical_vals", "_filter_ical_vals"),
    ("_sanitize_lot_name", "_normalize_lot_name"),
    ("_sanitize_message_text", "_normalize_message_text"),
    ("_sanitize_nemhandel_phone_number", "_normalize_nemhandel_phone_number"),
    ("_sanitize_number", "_normalize_number"),
    ("_sanitize_param_value", "_normalize_param_value"),
    ("_sanitize_peppol_endpoint_in_values", "_update_peppol_endpoint_in_values"),
    ("_sanitize_peppol_phone_number", "_normalize_peppol_phone_number"),
    ("_sanitize_phone", "_normalize_phone"),
    ("_sanitize_response", "_normalize_response"),
    ("_sanitize_upc", "_normalize_upc"),
    ("_sanitize_vals", "_normalize_vals"),
    ("_sanitize_values", "_normalize_values"),
    ("_sanitize_vcard_vals", "_filter_vcard_vals"),
    ("_sanitize_zip_name", "_normalize_zip_name"),
    (
        "_search_panel_sanitize_parent_hierarchy",
        "_search_panel_filter_parent_hierarchy",
    ),
    ("check_access_token", "is_access_token_valid"),
    ("check_patterns", "get_matching_pattern"),
    ("check_qr_iban_range", "is_qr_iban_range"),
    ("compute_depreciation_board", "_create_depreciation_entries"),
    ("resume_after_pause", "action_resume"),
    ("sanitize_args", "filter_request_args"),
    ("sanitize_communication", "normalize_communication"),
    ("sanitize_error_message", "redact_error_message"),
    ("sanitize_excel_sheet_name", "normalize_excel_sheet_name"),
    ("sanitize_for_xmlid", "normalize_for_xmlid"),
    ("sanitize_model_name", "check_model_name"),
    ("sanitize_peppol_endpoint", "normalize_peppol_endpoint"),
    ("sanitize_structured_reference", "normalize_structured_reference"),
    ("sanitize_vehicle_name", "normalize_vehicle_name"),
    ("sell_dispose", "action_sell_dispose"),
    ("set_to_cancelled", "action_cancel"),
    ("set_to_close", "_close"),
    ("set_to_draft", "action_reset_to_draft"),
    ("set_to_running", "action_reopen"),
)

_RENAMES_BY_MODEL = (
    ("modify", "action_modify", "asset.modify"),
    ("pause", "action_pause", "asset.modify"),
    ("pause", "_pause", "resource.asset"),
    ("validate", "action_confirm", "resource.asset"),
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
                    "base 1.65: %s.%s %s -> %s (%d row(s))",
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
                "base 1.65: ir_ui_view.arch_db %s() -> %s() (%d view(s))",
                old,
                new,
                cr.rowcount,
            )


def migrate(cr, version):
    if not version:
        return
    _rewrite_stored_python(cr)
    _rewrite_view_calls(cr)
    for old, new, model in _RENAMES_BY_MODEL:
        rename_in_stored_expressions(cr, old, new, model=model)
