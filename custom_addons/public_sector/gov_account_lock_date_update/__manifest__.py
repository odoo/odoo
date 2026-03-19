{
    "name": "AGI Gov - Accounting Lock Date Update (Community)",
    "version": "19.0.1.0.0",
    "summary": "Controlled workflow for updating company lock date with audit log",
    "description": "Community-style company lock date update with audit trail.",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "depends": [
        "account",
        "gov_account_fiscal_year",
        "gov_account_journal_lock_date",
    ],
    "data": [
        "security/account_lock_date_update_groups.xml",
        "security/ir.model.access.csv",
        "views/account_lock_date_log_views.xml",
        "views/account_lock_date_update_wizard_views.xml",
        "views/res_company_views.xml",
    ],
    "installable": True,
    "application": False,
}
