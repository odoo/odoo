{
    'name': 'Argentinean - Stock',
    'description': """Argentinean - Stock""",
    'category': 'Accounting/Localizations',
    'depends': ['l10n_ar', 'stock_account'],
    'data': [
        # data
        'data/ir_actions_server_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'data/uom_uom_data.xml',
        # Views
        'views/product_views.xml',
        'views/res_config_settings_views.xml',
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_picking_batch_views.xml',
        # Reports
        'views/report_delivery_guide.xml',
    ],
    'demo': [
        'demo/l10n_ar_stock_demo.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
