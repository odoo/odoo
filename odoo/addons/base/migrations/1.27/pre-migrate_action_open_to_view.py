import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

RENAMES = {
    "action_open_abandoned_cart_mail_template": "action_view_abandoned_cart_mail_template",
    "action_open_account_move": "action_view_account_move",
    "action_open_account_view": "action_view_account_view",
    "action_open_accrual_plan_employees": "action_view_accrual_plan_employees",
    "action_open_activities": "action_view_activities",
    "action_open_add_to_wave": "action_view_add_to_wave",
    "action_open_allocation_department": "action_view_allocation_department",
    "action_open_applications": "action_view_applications",
    "action_open_appraisal_survey_results": "action_view_appraisal_survey_results",
    "action_open_asset_ids": "action_view_asset_ids",
    "action_open_attachments": "action_view_attachments",
    "action_open_attendances": "action_view_attendances",
    "action_open_bank_balance_in_gl": "action_view_bank_balance_in_gl",
    "action_open_bank_reconcile_widget": "action_view_bank_reconcile_widget",
    "action_open_bank_reconciliation_widget": "action_view_bank_reconciliation_widget",
    "action_open_bank_reconciliation_widget_statement": "action_view_bank_reconciliation_widget_statement",
    "action_open_bank_transactions": "action_view_bank_transactions",
    "action_open_batch_picking": "action_view_batch_picking",
    "action_open_blocked_third_party_domains": "action_view_blocked_third_party_domains",
    "action_open_byproduct_change": "action_view_byproduct_change",
    "action_open_cash_discount_wizard": "action_view_cash_discount_wizard",
    "action_open_component_change": "action_view_component_change",
    "action_open_courses": "action_view_courses",
    "action_open_declarations": "action_view_declarations",
    "action_open_delivery_wizard": "action_view_delivery_wizard",
    "action_open_document": "action_view_document",
    "action_open_door": "action_view_door",
    "action_open_eco": "action_view_eco",
    "action_open_employee": "action_view_employee",
    "action_open_employee_appraisals": "action_view_employee_appraisals",
    "action_open_employee_salary_attachment": "action_view_employee_salary_attachment",
    "action_open_employees": "action_view_employees",
    "action_open_goal_template": "action_view_goal_template",
    "action_open_history": "action_view_history",
    "action_open_journal_invalid_statements": "action_view_journal_invalid_statements",
    "action_open_journal_view": "action_view_journal_view",
    "action_open_last_appraisal": "action_view_last_appraisal",
    "action_open_last_month_attendances": "action_view_last_month_attendances",
    "action_open_leave_department": "action_view_leave_department",
    "action_open_lines": "action_view_lines",
    "action_open_linked_assets": "action_view_linked_assets",
    "action_open_linked_config": "action_view_linked_config",
    "action_open_linked_loans": "action_view_linked_loans",
    "action_open_linked_orders": "action_view_linked_orders",
    "action_open_liquidity_transfers": "action_view_liquidity_transfers",
    "action_open_loan_entries": "action_view_loan_entries",
    "action_open_loyalty_cards": "action_view_loyalty_cards",
    "action_open_manual_reconciliation_widget": "action_view_manual_reconciliation_widget",
    "action_open_mes": "action_view_mes",
    "action_open_move": "action_view_move",
    "action_open_move_view": "action_view_move_view",
    "action_open_operation_form": "action_view_operation_form",
    "action_open_overtimes": "action_view_overtimes",
    "action_open_partner_followup_journal_items": "action_view_partner_followup_journal_items",
    "action_open_partner_view": "action_view_partner_view",
    "action_open_payslip": "action_view_payslip",
    "action_open_payslips": "action_view_payslips",
    "action_open_pdf_form_fields": "action_view_pdf_form_fields",
    "action_open_picking_client_action": "action_view_picking_client_action",
    "action_open_planned_request": "action_view_planned_request",
    "action_open_planning_slots": "action_view_planning_slots",
    "action_open_product_feeds": "action_view_product_feeds",
    "action_open_production": "action_view_production",
    "action_open_project": "action_view_project",
    "action_open_provider_form": "action_view_provider_form",
    "action_open_quality_check_picking": "action_view_quality_check_picking",
    "action_open_quality_check_wizard": "action_view_quality_check_wizard",
    "action_open_quality_checks": "action_view_quality_checks",
    "action_open_recommend_goals": "action_view_recommend_goals",
    "action_open_reconcile": "action_view_reconcile",
    "action_open_reconcile_statement": "action_view_reconcile_statement",
    "action_open_reconditioning_wizard": "action_view_reconditioning_wizard",
    "action_open_related_payslips": "action_view_related_payslips",
    "action_open_report": "action_view_report",
    "action_open_reward_wizard": "action_view_reward_wizard",
    "action_open_robots": "action_view_robots",
    "action_open_routing_change_operation": "action_view_routing_change_operation",
    "action_open_routing_change_quality_point": "action_view_routing_change_quality_point",
    "action_open_salary_attachments": "action_view_salary_attachments",
    "action_open_salary_configurator": "action_view_salary_configurator",
    "action_open_salary_rules": "action_view_salary_rules",
    "action_open_sale_order_spreadsheet": "action_view_sale_order_spreadsheet",
    "action_open_shop_floor": "action_view_shop_floor",
    "action_open_spreadsheet": "action_view_spreadsheet",
    "action_open_survey_inputs": "action_view_survey_inputs",
    "action_open_tax_return": "action_view_tax_return",
    "action_open_tax_view": "action_view_tax_view",
    "action_open_template_user": "action_view_template_user",
    "action_open_time_off_calendar": "action_view_time_off_calendar",
    "action_open_to_check": "action_view_to_check",
    "action_open_window": "action_view_window",
    "action_open_wizard": "action_view_wizard",
    "action_print_label": "action_view_label",
    "action_print_technical": "action_view_technical_sheet",
}

ORPHANED_MODULES = (
    "account_extract",
    "account_bank_statement_extract",
    "iap_extract",
    "hr_recruitment_extract",
)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return
    _rename_actions(cr)
    _drop_orphaned_views(cr)


def _rename_actions(cr: Cursor) -> None:
    renamed = 0
    for old, new in RENAMES.items():
        cr.execute(
            r"""
            UPDATE ir_ui_view
               SET arch_db = regexp_replace(
                       arch_db::text, '\y' || %s || '\y', %s, 'g'
                   )::jsonb
             WHERE arch_db::text ~ ('\y' || %s || '\y')
            """,
            (old, new, old),
        )
        renamed += cr.rowcount
    _logger.info(
        "Applied %d action renames across %d stored view arch(es)",
        len(RENAMES),
        renamed,
    )


def _drop_orphaned_views(cr: Cursor) -> None:
    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
             SELECT res_id FROM ir_model_data
              WHERE model = 'ir.ui.view' AND module = ANY(%s)
         )
        """,
        (list(ORPHANED_MODULES),),
    )
    dropped = cr.rowcount
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND module = ANY(%s)",
        (list(ORPHANED_MODULES),),
    )
    if dropped:
        _logger.info(
            "Dropped %d view(s) belonging to modules whose code is gone", dropped
        )
