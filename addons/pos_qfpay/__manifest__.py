# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS QFPay',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'author': 'Odoo S.A.',
    'summary': 'Integrate your POS with the QFPay terminal in Hong Kong',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_qfpay/static/src/**/*',
        ],
        'web.assets_tests': [
            'pos_qfpay/static/src/app/qfpay.js',
            'pos_qfpay/static/tests/tours/**/*',
        ],
    },
    'license': 'LGPL-3',
}
