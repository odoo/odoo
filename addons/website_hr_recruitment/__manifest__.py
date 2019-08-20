# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Online Jobs',
    'category': 'Website/Website',
    'sequence': 142,
    'version': '1.0',
    'summary': 'Manage your online hiring process',
    'description': "This module allows to publish your available job positions on your website and keep track of application submissions easily. It comes as an add-on of *Recruitment* app.",
    'depends': ['website_partner', 'hr_recruitment', 'website_mail', 'website_form'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_security.xml',
        'data/config_data.xml',
        'views/website_hr_recruitment_templates.xml',
        'views/hr_recruitment_views.xml',
        'views/hr_job_views.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'installable': True,
    'application': True,
}
