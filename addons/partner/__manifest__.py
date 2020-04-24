# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Partners',
    'version': '1.0',
    'category': 'Hidden',
    'description': """
This module holds the business definition of a basic partner, company, user
""",
    'depends': ['base', 'web'],
    'data': [
        'data/res_partner_data.xml',
        'data/res_partner_industry_data.xml',
        'data/res_partner_title_data.xml',
        'data/res_company_data.xml',
        'data/res_users_data.xml',
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/res_partner_title_views.xml',
        'views/res_partner_industry_views.xml',
        'views/res_users_views.xml',
        'views/report_templates.xml',
        'views/onboarding_views.xml',
        'wizard/base_document_layout_views.xml',
        'wizard/base_partner_merge_views.xml',
    ],
    'demo': [
        'data/res_partner_demo.xml',
        'data/res_partner_image_demo.xml',
        'data/res_partner_category_demo.xml',
        'data/res_users_demo.xml',
    ],
    'test': [],
    'installable': True,
    'auto_install': False,
}
