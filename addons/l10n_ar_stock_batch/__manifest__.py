{
    'name': 'Argentinean Stock - Batch Transfers',
    'description': """Bridge module for Argentine delivery guides on batch transfers.""",
    'category': 'Accounting/Localizations',
    'depends': ['l10n_ar_stock', 'stock_picking_batch'],
    'data': [
        'data/ir_actions_server_data.xml',
        'views/stock_picking_batch_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
