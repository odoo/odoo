# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Field Service Reports - Sale',
    'category': 'Hidden',
    'summary': 'Create Reports for Field service workers',
    'depends': ['industry_fsm_sale', 'industry_fsm_report'],
    'data': [
        'report/worksheet_custom_report_templates.xml',
        'views/product_template_views.xml',
        'views/project_views.xml',
        'data/industry_fsm_sale_report_data.xml',
    ],
    'demo': [
        'data/industry_fsm_sale_report_demo.xml',
    ],
    'auto_install': True,
    'post_init_hook': 'post_init',
    'license': 'OEEL-1',
}
