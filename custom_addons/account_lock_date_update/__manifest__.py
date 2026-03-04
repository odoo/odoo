{
    "name": "Account Lock Date Update",
    "version": "19.0.1.0.0",
    "summary": (
        "Controlled workflow for updating the company lock date "
        "with audit log - Kore clean-room build"
    ),
    "description": "Kore controlled company lock date update with audit trail.",
    "category": "Accounting/Accounting",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_fiscal_year",
        "account_journal_lock_date",
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

