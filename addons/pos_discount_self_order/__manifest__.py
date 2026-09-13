# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order - Discount',
    'category': 'Sales/Point Of Sale',
    'summary': 'Link module between PoS Self Order and PoS Discount',
    'depends': ['pos_self_order', 'pos_discount'],
    'auto_install': True,
    'assets': {
        'pos_self_order.assets': [
            'pos_discount/static/src/app/models/**/*',
            'pos_discount/static/src/app/utils/printer/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
