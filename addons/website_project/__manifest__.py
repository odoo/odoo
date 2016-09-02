# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Project",
    'description': """
Website portal for Project and Tasks
====================================
    """,
    'category': 'Website',
    'depends': ['project', 'website_portal'],
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'views/project_templates.xml',
    ],
    'demo': [
        'demo/project_demo.xml',
    ],
    'auto_install': True,
}
