# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": """E-waybill Stock""",
    "version": "1.0",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "stock", "l10n_in_edi_ewaybill",
    ],
    "description": """Ewaybill for Stock Picking""",
    "data": [
        "data/ewaybill_type_data.xml",
        "security/ir.model.access.csv",
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
