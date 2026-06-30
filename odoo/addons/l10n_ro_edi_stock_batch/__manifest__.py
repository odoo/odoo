{
    'name': 'Romania - E-Transport Batch Pickings',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'description': """
E-Transport implementation for Batch Pickings in Romania
    """,
    'depends': ['l10n_ro_edi_stock', 'stock_picking_batch'],
    'auto_install': True,
    'data': [
        'views/stock_picking_batch_views.xml',

        'report/report_picking_batch.xml',
    ],
    'installable': True,
    'license': "LGPL-3",
}
