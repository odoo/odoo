# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'POS Alipay',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with a Alipay QR code payment',
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_alipay/static/src/**/*',
        ],
    },
    'license': 'LGPL-3',
}
