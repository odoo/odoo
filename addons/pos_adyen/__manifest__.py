# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Adyen',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with an Adyen payment terminal',
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale', 'payment_adyen'],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_adyen/static/src/**/*',
        ],
        'point_of_sale.payment_terminals': [
            'pos_adyen/static/src/app/utils/payment/payment_adyen.js',
            'pos_adyen/static/src/app/models/pos_payment.js',
        ],
        'web.assets_tests': [
            'pos_adyen/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_adyen/static/tests/unit/data/**/*'
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
