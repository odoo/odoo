# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Spain - Sale Stock - DeCA",
    'version': '1.1',
    'category': 'Accounting/Localizations',
    'description': """
This module lets the user generate the DeCA document
(Documento electrónico de Control Administrativo) from a stock.picking
delivery, adapted from the CMR report of stock_fleet and adding the fields required by law.
    """,
    'depends': [
        'l10n_es',
        'stock_picking_batch',
    ],
    'data': [
        "views/stock_picking_views.xml",
        "views/stock_picking_batch_views.xml",
        "views/ir_attatchment_views.xml",
        "report/report_picking_deca.xml"
    ],
    'assets': {
        'web.report_assets_common': [
            'l10n_es_sale_stock/static/src/css/report_picking_deca.scss',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
