# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Bridge module for website_sale_referral and crm",

    'summary': """
        Bridge module for website_sale_referral and crm""",

    'description': """
        Allows to create lead when a referral is made
    """,
    'category': 'Website/Website',
    'version': '0.1',
    'depends': ['website_sale_referral', 'crm'],
    'data': [
        'data/website_crm_referral_data.xml',
        'views/res_config_settings_views.xml',
        'views/referral_template.xml',
        'views/crm_lead_views.xml',
        'views/sale_views.xml',
    ],
    'auto_install': True,
}
