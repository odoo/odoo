# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Website Project Issue',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds project issues inside your account's page on website if project_issue and website_portal are installed.
==================================================================================================
    """,
    'depends': ['project_issue', 'website_portal'],
    'data': [
        'security/portal_security.xml',
        'security/ir.model.access.csv',
        'views/project_issue_templates.xml',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}
