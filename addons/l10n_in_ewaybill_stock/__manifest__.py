{
    "name": "Indian - E-waybill Stock",
    "version": "1.1",
    "category": "Accounting/Localizations/EDI",
    "description": """
Indian E-waybill for Stock
==========================

This module enables users to create E-waybill from Inventory App without generating an invoice
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "l10n_in_stock",
        "l10n_in_ewaybill",
    ],
    "data": [
        "security/ir.access.csv",
        "data/ewaybill_type_data.xml",
        "views/l10n_in_ewaybill_views.xml",
        "views/stock_picking_views.xml",
        "reports/ewaybill_report_inherit.xml",
    ],
    "auto_install": True,
}
