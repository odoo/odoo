{
    "name": "Account Move Template",
    "version": "19.0.1.0.0",
    "summary": "Recurring journal entry templates for structured month-end close - Kore clean-room build",
    "category": "Accounting/Accounting",
    "author": "Kore",
    "license": "LGPL-3",
    "depends": [
        "account",
        "mail",
    ],
    "data": [
        "security/account_move_template_groups.xml",
        "security/ir.model.access.csv",
        "views/account_move_template_views.xml",
        "views/account_move_template_run_wizard_views.xml",
        "views/account_move_template_menus.xml",
    ],
    "installable": True,
    "application": False,
}

