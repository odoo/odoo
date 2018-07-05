# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Project',
    'version': '1.1',
    'website': 'https://www.odoo.com/page/project-management',
    'category': 'Project',
    'sequence': 10,
    'summary': 'Projects, Tasks',
    'depends': [
        'base_setup',
        'product',
        'analytic',
        'mail',
        'portal',
        'resource',
        'web',
        'web_planner',
        'web_tour',
    ],
    'description': "",
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'report/project_report_views.xml',
        'views/project_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'views/project_templates.xml',
        'views/project_portal_templates.xml',
        'data/web_planner_data.xml',
        'data/project_mail_template_data.xml',
        'wizard/project_task_merge_wizard_views.xml',
        'data/project_data.xml',
    ],
    'qweb': ['static/src/xml/project.xml'],
    'demo': ['data/project_demo.xml'],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
