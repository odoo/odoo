# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Sale Coupon",
    'summary': """Allows to use discount coupons in ecommerce orders""",
    'description': """Integrate coupons mechanism in ecommerce.""",
    'category': 'Website',
    'version': '1.0',
    'depends': ['website_sale', 'sale_coupon'],
    'data': [
        'views/website_sale_templates.xml',
        'views/res_config_settings_views.xml',
        'views/sale_coupon_program_views.xml',
    ],
    'auto_install': True,
}
