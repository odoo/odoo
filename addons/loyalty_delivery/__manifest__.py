# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Coupons & Loyalty - Delivery',
    'summary': "Add a free shipping option to your rewards",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['loyalty', 'delivery'],
    'data': [
        'data/loyalty_delivery_data.xml',
        'views/loyalty_reward_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}
