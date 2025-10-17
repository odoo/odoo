# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indian - Sale Report(GST)',
    'description': """GST Sale Report""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_in',
        'sale',
    ],
    'data': [
        'views/sale_order_views.xml',
    ],
    'demo': [
        'data/product_demo.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
