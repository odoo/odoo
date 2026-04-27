# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI for POS",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI for POS
================================
Provides electronic invoicing for Brazil through Avatax in the POS.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": ["l10n_br_edi", "point_of_sale"],
    "demo": ["data/product_product_demo.xml"],
    "data": [
        "views/pos_order_views.xml",
        "views/pos_payment_method_views.xml",
        "views/product_template_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "auto_install": True,
    "assets": {
        "point_of_sale._assets_pos": ["l10n_br_edi_pos/static/src/**/*"],
        "web.assets_tests": [
            "l10n_br_edi_pos/static/tests/tours/**/*",
        ],
    },
}
