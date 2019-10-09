# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Sale Coupon",
    'summary': "Use discount coupons in sales orders",
    'description': """Integrate coupon mechanism in sales orders.""",
    'category': 'Sales/Sales',
    'version': '1.0',
    'depends': ['coupon', 'sale_management'],
    'data': [
        'wizard/sale_coupon_apply_code_views.xml',
        'views/sale_order_views.xml',
        'views/sale_coupon_views.xml',
        'views/sale_coupon_program_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
    ],
}
