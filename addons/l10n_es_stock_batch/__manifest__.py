# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Spain - Stock - DeCA Batch Transfers",
    'version': '1.0',
    'category': 'Accounting/Localizations',
    'description': """
Generate the DeCA (Documento electrónico de Control Administrativo)
for all the deliveries of a batch transfer at once.
    """,
    'depends': [
        'l10n_es_stock',
        'stock_picking_batch',
    ],
    'data': [
        "views/stock_picking_batch_views.xml",
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
