# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Customer Referral',
    'category': 'Website/Website',
    'summary': 'Generate and follow-up referral for customers',
    'version': '1.0',
    'description': """
Help the company to get more leads by leveraging his existing customers' base. Main objective: everyone can refer a prospect. If the prospect subscribes, the referrer is rewarded.""",
    'depends': ['sale_management', 'website', 'link_tracker', 'mail'],
    'qweb': ['static/src/xml/referral_tracking_single_sub_template.xml'],
    'data': [
        'security/ir.model.access.csv',
        'data/website_sale_referral_data.xml',
        'views/res_config_settings_views.xml',
        'views/referral_template.xml',
        'views/referral_views.xml',
        'views/sale_views.xml',
    ],
}
