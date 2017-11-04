# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Jobs',
    'category': 'Website',
    'sequence': 142,
    'version': '1.0',
    'summary': 'Job Descriptions And Application Forms',
    'description': "",
    'depends': ['website_partner', 'hr_recruitment', 'website_mail', 'website_form'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_security.xml',
        'data/config_data.xml',
        'views/website_hr_recuitment_snippets.xml',
        'views/website_hr_recruitment_templates.xml',
        'views/hr_recruitment_views.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'installable': True,
}
