{
    "name": "AGI Gov - Accounting Journal Lock Date (Community)",
    "version": "19.0.1.0.0",
    "summary": "Per-journal lock dates for controlled period close",
    "description": "Community-style journal lock date controls aligned to GOV suite.",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "depends": [
        "account",
        "gov_account_fiscal_year",
    ],
    "data": [
        "security/account_journal_lock_date_groups.xml",
        "security/ir.model.access.csv",
        "views/account_journal_views.xml",
        "views/account_journal_lock_date_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
