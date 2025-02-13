# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': """Indian - E-waybill Stock""",
    'version': '1.1',
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_in_stock',
        'l10n_in_ewaybill',
    ],
    'description': """
Indian E-waybill for Stock
==========================

This module enables users to create E-waybill from Inventory App without generating an invoice
    """,
    'data': [
        'security/ir.model.access.csv',
        'data/ewaybill_type_data.xml',
        'views/l10n_in_ewaybill_views.xml',
        'views/stock_picking_views.xml',
        'report/ewaybill_report_inherit.xml'
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
