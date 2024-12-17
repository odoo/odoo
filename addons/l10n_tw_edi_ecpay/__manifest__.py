# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Taiwan - E-invoicing",
    "countries": ["tw"],
    "version": "1.0",
    "category": "Accounting/Localizations/EDI",
    "summary": """E-invoicing using ECpay""",
    "description": """
        Taiwan - E-invoicing
        =====================
        This module allows the user to send their invoices to the Ecpay system.
    """,
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "l10n_tw",
    ],
    "data": [
        "views/res_config_setting_view.xml",
        "views/account_tax.xml",
        "views/account_move_view.xml",
        "views/account_move_reversal_view.xml",
        "report/ecpay_invoice_report.xml",
    ],
    "assets": {
        "web.report_assets_common": [
            "l10n_tw_edi_ecpay/static/src/**/*",
        ],
    },
    "installable": True,
}
