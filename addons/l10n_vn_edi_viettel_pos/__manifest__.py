# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Vietnam - POS E-invoicing""",
    'icon': '/account/static/description/l10n.png',
    "version": "1.0",
    'countries': ['vn'],
    "category": "Accounting/Localizations/EDI",
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/vietnam.html',
    "depends": [
        "l10n_vn_edi_viettel",
        "point_of_sale",
    ],
    "summary": "POS E-invoicing using SInvoice by Viettel",
    "description": """
Vietnam - POS E-invoicing
=========================
Using SInvoice by Viettel
    """,
    'data': [
        "data/res_partner_data.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_vn_edi_viettel_pos/static/src/**/*',
        ],
    },
    "auto_install": True,
    "license": "LGPL-3",
}
