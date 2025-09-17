# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Vietnam - E-invoicing""",
    'icon': '/account/static/description/l10n.png',
    "version": "1.0",
    'countries': ['vn'],
    "category": "Accounting/Localizations/EDI",
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/vietnam.html',
    "depends": [
        "l10n_vn",
    ],
    "summary": "E-invoicing using SInvoice by Viettel",
    "description": """
Vietnam - E-invoicing
=====================
Using SInvoice by Viettel
    """,
    "data": [
        'security/ir.model.access.csv',
        "views/account_move_views.xml",
        "views/res_config_settings_views.xml",
        "views/res_partner_views.xml",
        "views/sinvoice_views.xml",
        "wizard/account_move_reversal_view.xml",
        "wizard/l10n_vn_edi_cancellation_request_views.xml",
    ],
    "installable": True,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
}
