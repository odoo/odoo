{
    'name': 'Argentinean - Stock',
    'version': '1.0',
    'description': """Argentinean - Stock""",
    'category': 'Accounting/Localizations',
    'depends': ['l10n_ar', 'stock_account'],
    'data': [
        # data
        'data/mail_template_data.xml',
        # Views
        'views/stock_picking_type_views.xml',
        'views/stock_picking_views.xml',
        # Reports
        'views/report_delivery_guide.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
