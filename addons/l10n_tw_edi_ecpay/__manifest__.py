# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Taiwan - E-invoicing",
    "countries": ["tw"],
    "version": "1.0",
    'icon': '/account/static/description/l10n.png',
    "category": "Accounting/Localizations/EDI",
    "summary": """E-invoicing using ECpay""",
    "description": """
        Taiwan - E-invoicing
        =====================
        This module allows the user to send their invoices to the Ecpay system.
    """,
    "website": "https://www.odoo.com",
    'author': 'Odoo S.A.',
    "license": "LGPL-3",
    "depends": ["l10n_tw"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_setting_view.xml",
        "views/account_tax.xml",
        "views/account_move_view.xml",
        "views/account_move_reversal_view.xml",
        "views/l10n_tw_edi_invoice_cancel_view.xml",
        "views/l10n_tw_edi_invoice_print_view.xml",
    ],
    "installable": True,
}
