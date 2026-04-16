# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """Vietnam - Delivery E-invoicing""",
    'icon': '/account/static/description/l10n.png',
    "author": "Odoo S.A.",
    'countries': ['vn'],
    "category": "Accounting/Localizations/EDI",
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/vietnam.html',
    "depends": [
        "l10n_vn_edi_viettel",
        "stock",
    ],
    "summary": "Delivery E-invoicing using SInvoice by Viettel",
    "description": """
Vietnam - Delivery E-invoicing
==============================
Using SInvoice by Viettel
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/stock_warehouse_views.xml",
        "views/stock_picking_views.xml",
        "wizard/wizard_send_views.xml",
    ],
    "auto_install": True,
    "license": "LGPL-3",
}
