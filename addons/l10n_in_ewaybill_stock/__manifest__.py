# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": """Indian - E-waybill Stock""",
    "version": "1.0",
    'countries': ['in'],
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "l10n_in_stock",
        "l10n_in_edi_ewaybill",
    ],
    "description": """
Indian E-waybill for Stock
==========================

This module enables users to create E-waybill from Inventory App without generating an invoice
    """,
    "data": [
        'security/ir_rules.xml',
        "security/ir.model.access.csv",
        "data/ewaybill_type_data.xml",
        "views/l10n_in_ewaybill_views.xml",
        "views/stock_picking_views.xml",
        "report/ewaybill_report_views.xml",
        "report/ewaybill_report.xml",
        "wizard/l10n_in_ewaybill_cancel_views.xml",
    ],
    'installable': True,
    'auto_install': True,
    "license": "LGPL-3",
}
