# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Brazilian Accounting EDI for eCommerce",
    "version": "1.0",
    "description": """
Brazilian Accounting EDI for eCommerce
======================================
Allows tax calculation and EDI for eCommerce users.
""",
    "category": "Accounting/Localizations/EDI",
    "license": "OEEL-1",
    "depends": ["l10n_br_edi_sale", "website_sale_external_tax"],
    "data": [
        "data/delivery_data.xml",
        "views/delivery_carrier_views.xml",
    ],
    "demo": ["data/delivery_demo.xml"],
    "auto_install": True,
}
