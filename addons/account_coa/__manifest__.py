{
    "name": "Chart of Accounts",
    "version": "1.0",
    "category": "Accounting/Accounting",
    "summary": "Chart of Accounts foundation",
    "description": """
Chart of Accounts
=================
Provides the core Chart of Accounts structure: account types, codes,
tags, and multi-company code mappings.  Designed as a lightweight
foundation that heavier accounting modules (``account``, ``account_accountant``)
depend on.
    """,
    "author": "Odoo S.A., AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "base",
    ],
    "data": [
        "security/ir.access.csv",
        "views/account_account_views.xml",
        "views/account_account_tag_views.xml",
    ],
}
