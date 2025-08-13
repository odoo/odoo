{
    'name': 'Portugal - Stock',
    'version': '1.0',
    'description': """Stock module for Portugal which allows hash and QR code on stock pickings""",
    'category': 'Accounting/Localizations/Stock',
    'depends': [
        'stock',
        'l10n_pt',
    ],
    'data': [
        'data/ir_cron.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_type_views.xml',
        'views/res_config_settings_views.xml',
        'report/l10n_pt_stock_hash_integrity_templates.xml',
        'report/report_deliveryslip.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
