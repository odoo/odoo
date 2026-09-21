{
    "name": "IBAN Bank Accounts",
    "category": "Accounting/Accounting",
    "description": """
This module installs the base for IBAN (International Bank Account Number) bank accounts and checks for it's validity.
======================================================================================================================

The ability to extract the correctly represented local accounts from IBAN accounts
with a single statement.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "views/partner_view.xml",
        "views/setup_wizards_view.xml",
    ],
    "demo": [
        "demo/res_partner_bank_account_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_iban/static/src/components/**/*",
        ],
        "web.assets_unit_tests": [
            "account_iban/static/src/tests/**/*",
        ],
    },
}
