# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sale Loyalty',
    'summary': 'Use discounts and loyalty programs in sales orders',
    'description': 'Integrate discount and loyalty programs mechanisms in sales orders.',
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['sale', 'loyalty'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'data/sale_loyalty_data.xml',
        'wizard/sale_loyalty_coupon_wizard_views.xml',
        'wizard/sale_loyalty_reward_wizard_views.xml',
        'views/loyalty_card_views.xml',
        'views/loyalty_program_views.xml',
        'views/sale_order_views.xml',
        'views/templates.xml',
    ],
    'license': 'LGPL-3',
}
