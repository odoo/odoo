{
    "name": "Jordan Accounting EDI for POS",
    "version": "1.0",
    "description": """
Jordan Accounting EDI for POS
=============================
Provides electronic invoicing for Jordan in the POS.
""",
    "category": "Accounting/Localizations/EDI",
    'author': 'Odoo S.A.',
    "license": "OEEL-1",
    "depends": ["l10n_jo_edi", "point_of_sale"],
    "demo": ["demo/demo_company.xml"],
    "data": [
        "views/pos_order_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "auto_install": True,
    "assets": {
        "point_of_sale._assets_pos": ["l10n_jo_edi_pos/static/src/**/*"],
    },
}
