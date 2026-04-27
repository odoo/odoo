# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Tyro',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Integrate your POS with a Tyro payment terminal (AU)',
    'data': [
        'data/pos_tyro_data.xml',
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'web.assets_backend': [
            'pos_tyro/static/src/urls.js',
            'pos_tyro/static/src/actions/**/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_tyro/static/src/urls.js',
            'pos_tyro/static/src/app/**/*',
            'pos_tyro/static/src/overrides/**/*',
        ],
    },
    'license': 'OEEL-1',
}
