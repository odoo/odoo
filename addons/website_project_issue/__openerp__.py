# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Website Project Issue',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds issue menu and features to your portal if project_issue and portal are installed.
==================================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['project_issue','portal', 'website'],
    'data': [
        'security/portal_security.xml',
        'security/ir.model.access.csv',
        'portal_project_issue_view.xml',
        'website_project_issue_view.xml',
        'views/portal_project_issue.xml',
    ],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}
