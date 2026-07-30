# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": """E-waybill Stock""",
    "version": "1.0",
    "category": "Accounting/Localizations/EDI",
    "depends": [
        "stock", "l10n_in", "l10n_in_edi", "l10n_in_edi_ewaybill",
    ],
    "description": """Ewaybill for Stock Movement""",
    "data": [
        "security/ir.model.access.csv",
        "wizard/ewaybill_update_part_b_views.xml",
        "wizard/ewaybill_update_transporter_views.xml",
        "wizard/ewaybill_extend_validity_views.xml",
        "views/l10n_in_ewaybill_views.xml",
        "views/stock_picking_views.xml",
        "report/ewaybill_report_views.xml",
        "report/ewaybill_report.xml",
        ],
    "installable": True,
    "license": "LGPL-3",
}
