# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Accounting Customer Statements",
    "version": "1.0",
    "author": "Odoo Sa",
    "description": """
Add Customer Statements to the accounting module
================================================
Auto installed for users in Australia, India and New Zealand as it is customary there.
    """,
    "category": "Accounting/Localizations/Reporting",
    "depends": ["account_reports"],
    "data": [
        'report/customer_statements_report.xml',
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_account_customer_statements/static/src/components/**/*",
        ],
    },
    "installable": True,
    "license": "OEEL-1",
}
