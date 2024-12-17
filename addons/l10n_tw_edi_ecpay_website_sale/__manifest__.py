# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Taiwan - E-invoicing Ecommerce",
    "category": "Website Sale/Localizations/EDI",
    "summary": """ECpay E-invoice bridge module for Ecommerce""",
    "description": """
        This bridge module allows the user to input Ecpay information in ecommerce for sending their invoices to the Ecpay system
    """,
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "l10n_tw_edi_ecpay",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/templates.xml"
    ],
    "assets": {
        "web.assets_frontend": [
            "l10n_tw_edi_ecpay_website_sale/static/src/**/*"
        ],
        'web.assets_tests': [
            'l10n_tw_edi_ecpay_website_sale/static/tests/**/*',
        ],
    },
    "auto_install": True,
}
