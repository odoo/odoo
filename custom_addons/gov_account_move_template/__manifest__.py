{
    "name": "AGI Gov - Accounting Move Template (Community)",
    "version": "19.0.1.0.0",
    "summary": "Recurring journal entry templates for structured period close",
    "category": "Accounting/Accounting",
    "author": "AGI Gov",
    "license": "LGPL-3",
    "depends": [
        "gov_base",
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
