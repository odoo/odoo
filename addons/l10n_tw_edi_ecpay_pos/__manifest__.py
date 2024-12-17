# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Taiwan - E-invoicing Pos",
    "version": "1.0",
    "category": "Point of sale/Localizations/EDI",
    "summary": """ECpay E-invoice bridge module for POS""",
    "description": """
        This bridge module allows the user to input Ecpay information in pos for sending their invoices to the Ecpay system
    """,
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "l10n_tw_edi_ecpay",
    ],
    "data": [
        "data/res_partner_data.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "l10n_tw_edi_ecpay_pos/static/src/**/*"
        ],
    },
    "auto_install": True,
}
