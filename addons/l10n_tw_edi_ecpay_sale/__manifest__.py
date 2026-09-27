# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Taiwan - E-invoicing Sales",
    "category": "Website Sale/Localizations/EDI",
    "summary": """ECPay E-invoice bridge module for Sales""",
    "description": """
        This bridge module allows the user to input ECPay information in Sales for sending their invoices to the ECPay system
    """,
    'author': 'Odoo S.A.',
    "license": "LGPL-3",
    "depends": [
        "sale",
        "l10n_tw_edi_ecpay",
    ],
    "data": [
        "views/sale_order_views.xml",
    ],
    "auto_install": True,
}
