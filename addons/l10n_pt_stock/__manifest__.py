{
    'name': 'Portugal - Stock',
    'version': '1.0',
    'countries': ['pt'],
    'description': """Stock module for Portugal which allows hash and QR code on stock pickings""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'stock',
        'l10n_pt',
    ],
    'auto_install': [
        'stock',
        'l10n_pt',
    ],
    'data': [
        'data/data.xml',
        'data/ir_cron.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'report/l10n_pt_stock_hash_integrity_templates.xml',
        'report/report_deliveryslip.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
