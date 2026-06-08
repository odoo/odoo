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
        # Views
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        # Reports
        'views/report_delivery_guide.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
