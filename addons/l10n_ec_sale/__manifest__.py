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
        'views/sale_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}
