# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PoS DPO',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Integrate your POS with DPO payment terminal.',
    'data': [
        'views/pos_payment_method_views.xml',
        'views/pos_payment_views.xml',
    ],
    'depends': ['point_of_sale'],
    'installable': True,
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_dpo/static/src/**/*',
        ],
    },
    'author': 'Odoo India Pvt. Ltd.',
    'license': 'LGPL-3',
}
