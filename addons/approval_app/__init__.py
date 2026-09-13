from . import models

_ENGINE_SHELL_XMLIDS = [
    "approval_attachment_training_program",
    "approval_category_approver_business_trip",
    "approval_category_data_borrow_items",
    "approval_category_data_business_trip",
    "approval_category_data_car_rental_application",
    "approval_category_data_contract_approval",
    "approval_category_data_general_approval",
    "approval_category_data_job_referral_award",
    "approval_category_data_payment_application",
    "approval_category_data_procurement",
    "approval_request_borrow_laptop",
    "approval_request_borrow_projector",
    "approval_request_business_trip_london",
    "approval_request_business_trip_paris",
    "approval_request_business_trip_tokyo",
    "approval_request_car_rental_cancelled",
    "approval_request_car_rental_client_visit",
    "approval_request_contract_acme",
    "approval_request_contract_refused",
    "approval_request_general_office_renovation",
    "approval_request_general_training_program",
    "approval_request_job_referral",
    "approval_request_payment_urgent",
    "approval_request_payment_vendor",
    "approvals_approval_menu",
    "approvals_approval_menu_all",
    "approvals_approval_menu_inbox",
    "approvals_approval_menu_to_review",
    "approvals_category_menu_config",
    "approvals_category_menu_new",
    "approvals_menu_config",
    "approvals_menu_manager",
    "approvals_menu_root",
    "approvals_request_menu_delegate",
    "approvals_request_menu_history",
    "approvals_request_menu_my",
    "approvals_template_menu_config",
    "group_finance_approvers",
    "menu_approval_binding",
    "menu_approval_refusal_reason",
    "menu_approval_report",
    "menu_approval_rules",
    "partner_acme_corp",
    "partner_john_doe",
    "partner_tech_solutions",
    "user_approval_manager",
    "user_approver_1",
    "user_approver_2",
    "user_approver_3",
    "user_employee",
]


def _adopt_engine_shell(cr):
    """Move the records `approval` 2.2 and earlier shipped as the application here.

    Moving the external ids makes this module update those records instead of
    creating second copies beside them. Called by `approval`'s 2.3 pre-migrate.
    """
    cr.execute(
        """
        UPDATE ir_model_data
           SET module = 'approval_app'
         WHERE module = 'approval'
           AND name = ANY(%s)
        """,
        [_ENGINE_SHELL_XMLIDS],
    )


def _pre_init_refuse_to_reset_the_engine_shell(env):
    """An install loads data in init mode, which rewrites noupdate records.

    On a database that already holds the categories and demo `approval` used to
    ship, this module must be upgraded into them, never installed over them.
    `approval`'s 2.3 pre-migrate arranges that; reaching an install here means it
    did not run in this load, or ran in an earlier one that failed after it.
    """
    env.cr.execute(
        """
        SELECT module
          FROM ir_model_data
         WHERE module IN ('approval', 'approval_app')
           AND name = ANY(%s)
         LIMIT 1
        """,
        [_ENGINE_SHELL_XMLIDS],
    )
    row = env.cr.fetchone()
    if not row:
        return
    if row[0] == "approval":
        raise RuntimeError(
            "approval_app takes over records approval 19.0.2.2.0 and earlier "
            "shipped, and only approval's 19.0.2.3.0 migration hands them over. "
            "Upgrade approval in the same run: -u approval,<modules>."
        )
    raise RuntimeError(
        "approval_app already owns the records approval handed over, and "
        "installing it would reset them to their shipped values. Mark it for "
        "upgrade instead: UPDATE ir_module_module SET state = 'to upgrade' "
        "WHERE name = 'approval_app'; then run -u approval_app."
    )
