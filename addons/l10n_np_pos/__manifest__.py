# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Nepal - Point of Sale',
    'icon': '/account/static/description/l10n.png',
    'countries': ['np'],
    'description': """
 Nepal - Point of Sale
    """,
    'category': 'Accounting/Localizations/Point of Sale',
    'depends': [
        'l10n_np',
        'point_of_sale',
    ],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_np_pos/static/src/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
