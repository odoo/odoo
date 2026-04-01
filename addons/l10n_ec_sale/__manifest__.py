# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ecuador - Sale',
    'version': '1.0',
    'description': """Ecuador Sale""",
    'category': 'Accounting/Localizations/Sale',
    'depends': [
        'l10n_ec',
        'sale',
    ],
    'data': [
        'data/payment_method_data.xml',
        'views/payment_method_views.xml',
        'views/sale_order_views.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
