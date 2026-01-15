# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Loyalty - Delivery',
    'summary': 'Adds free shipping mechanism in sales orders',
    'description': 'Integrate free shipping in sales orders.',
    'category': 'Sales/Sales',
    'data': [
        'views/loyalty_reward_views.xml',
    ],
    'depends': ['sale_loyalty', 'delivery'],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
