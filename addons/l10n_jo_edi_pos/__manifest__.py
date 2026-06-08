{
    "name": "Jordan Accounting EDI for POS",
    "author": "Odoo S.A.",
    "countries": ["jo"],
    "description": """
Jordan Accounting EDI for POS
=============================
Provides electronic invoicing for Jordan in the POS.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "LGPL-3",
    "depends": ["l10n_jo_edi", "pos_edi_ubl"],
    "demo": ["demo/demo_company.xml"],
    "data": [
        "receipt/pos_order_receipt.xml",
        "views/pos_order_views.xml",
        "views/pos_payment_method_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "auto_install": True,
    "assets": {
        "point_of_sale._assets_pos": ["l10n_jo_edi_pos/static/src/**/*"],
        "web.assets_tests": [
            "l10n_jo_edi_pos/static/tests/tours/**/*",
        ],
    },
}
