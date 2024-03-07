# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Ecuadorian Point of Sale',
    'countries': ['ec'],
    'version': '1.0',
    'category': 'Accounting/Localizations/Website',
    'description': """Make Point of Sale work for Ecuador.""",
    'depends': [
        'point_of_sale',
        'l10n_ec',
    ],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'l10n_ec_pos/static/tests/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
