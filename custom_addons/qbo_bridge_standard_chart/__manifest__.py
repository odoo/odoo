{
    "name": "QBO Bridge Standard Chart",
    "version": "19.0.1.0.0",
    "category": "Accounting/Localization",
    "summary": "Canonical chart workspace for QBO Bridge",
    "description": """
        Dedicated master chart of accounts workspace for QBO Bridge.

        Features
        --------
        * Stores the umbrella company's canonical chart of accounts
        * Imports or refreshes the chart from the enriched CSV seed file
        * Links standard accounts to QBO bridge rules and company accounts
        * Pushes selected standard accounts out to mapped Kodoo/QBO companies
    """,
    "author": "Kodoo",
    "website": "https://kodoo.dev",
    "depends": [
        "qbo_bridge",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/qbo_standard_account_views.xml",
        "views/qbo_account_bridge_rule_views.xml",
        "views/qbo_standard_chart_import_wizard_views.xml",
        "views/qbo_standard_account_sync_wizard_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
