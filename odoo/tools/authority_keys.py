import typing
from collections.abc import Mapping

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_AUTHORITY_KEYS: dict[str, str] = {}


def declare_authority_keys(owner: str, *keys: str) -> None:
    for key in keys:
        _AUTHORITY_KEYS.setdefault(key, owner)


def authority_keys() -> Mapping[str, str]:
    return dict(_AUTHORITY_KEYS)


def is_authority_key(key: typing.Any) -> bool:
    return key in _AUTHORITY_KEYS


def strip_authority_keys(context: typing.Any, door: str = "") -> typing.Any:
    if not isinstance(context, Mapping):
        return context
    dropped = [key for key in context if key in _AUTHORITY_KEYS]
    if not dropped:
        return context
    _debug.logic("context.authority_keys_stripped", door=door, keys=sorted(dropped))
    return {key: value for key, value in context.items() if key not in _AUTHORITY_KEYS}


declare_authority_keys(
    "base",
    "uid",
    "api_scope_id",
    "install_mode",
    "install_module",
    "_force_unlink",
    "bypass_locked_check",
    "force_deactivate",
    "force_company",
)
declare_authority_keys("automation", "__automation_bookkeeping")
declare_authority_keys("mail", "mail_notify_security_skip")
declare_authority_keys(
    "account",
    "skip_readonly_check",
    "skip_account_deprecation_check",
    "force_delete",
    "skip_account_review_check",
    "skip_invoice_line_sync",
    "skip_account_move_synchronization",
)
declare_authority_keys(
    "approval", "approval_binding_admitted", "approval_keep_on_subject_change"
)
declare_authority_keys("approval_res_users_deletion", "approval_skip")
declare_authority_keys("stock", "skip_validation_check")
declare_authority_keys("stock_delivery", "allow_delivery_cost_update")
declare_authority_keys("mrp", "allow_more")
declare_authority_keys("maintenance", "skip_maintenance_reservations")
declare_authority_keys(
    "hr_holidays",
    "leave_skip_date_check",
    "leave_skip_state_check",
    "allocation_skip_state_check",
    "skip_copy_check",
)
declare_authority_keys(
    "hr_work_entry", "hr_work_entry_no_check", "work_entry_skip_validation"
)
declare_authority_keys("point_of_sale", "bypass_payment_method_ids_forbidden_change")
declare_authority_keys("resource_asset", "skip_meter_monotonic")
declare_authority_keys("date_range", "bypass_company_validation")
declare_authority_keys("integration", "allow_http_production")
declare_authority_keys("google_calendar", "skip_event_permission")
declare_authority_keys("l10n_in_edi", "l10n_in_edi_force_cancel")
declare_authority_keys("l10n_latam_check", "l10n_ar_skip_remove_check")
declare_authority_keys("quality_control", "skip_check", "no_checks")
declare_authority_keys("l10n_au_hr_payroll_account", "allow_ffr")
declare_authority_keys("knowledge", "knowledge_member_skip_writable_check")
declare_authority_keys(
    "account_credit", "credit_override", "skip_credit_exceeded_authorization"
)
declare_authority_keys("product_abc_classification", "skip_weight_total_check")
declare_authority_keys("stock_lot_rule", "skip_lot_rule_validation")
declare_authority_keys("mockup_studio", "skip_document_folder_check")
declare_authority_keys(
    "l10n_mx_avoid_reversal_entry", "force_draft_in_fx_and_caba_entries"
)
declare_authority_keys("document_l10n_mx_edi", "skip_sat_confirmation")
