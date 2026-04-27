# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Ecuadorian Delivery Guide",
    "version": "1.1",
    "description": """
The delivery guide (Guía de Remisión) is needed as a proof
that you are sending goods between A and B.

It is only when a delivery order is validated that you can create the delivery
guide.
""",
    "author": "TRESCLOUD",
    "category": "Accounting/Localizations/EDI",
    "license": "OPL-1",
    "depends": [
        "stock_account",
        "l10n_ec_edi",
    ],
    "data": [
        # Views
        "views/stock_warehouse_view.xml",
        "views/stock_picking_view.xml",
        # Reports
        'views/report_delivery_guide.xml',
        # Data
        'data/edi_delivery_guide.xml',
        'data/mail_template_data.xml',
        'data/cron_data.xml',
    ],
    "installable": True,
    "auto_install": True,
}
