# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Spain - Sale Stock - DeCA",
    'version': '1.1',
    'category': 'Accounting/Localizations',
    'description': """
This module lets the user generate the DeCA document
(Documento electrónico de Control Administrativo) from a stock.picking
delivery using the CMR report from stock_fleet as a template, adding required additional fields.
    """,
    'depends': [
        'l10n_es',
        'stock_fleet',
        'stock_picking_batch',
    ],
    'data': [
        "views/stock_picking_views.xml",
        "views/stock_picking_batch_views.xml",
        "views/ir_attatchment_views.xml",
        "report/report_picking_deca.xml"
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
