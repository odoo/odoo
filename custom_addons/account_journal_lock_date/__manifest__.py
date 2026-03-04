{
    "name": "Account Journal Lock Date",
    "version": "19.0.1.0.0",
    "summary": (
        "Per-journal lock dates for structured month-end close - "
        "Kore clean-room build"
    ),
    "description": "Kore journal-level lock date controls for controlled period close.",
    "category": "Accounting/Accounting",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_fiscal_year",
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

