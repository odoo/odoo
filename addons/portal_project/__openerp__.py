# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Portal Project',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description': """
This module adds project menu and features (tasks) to your portal if project and portal are installed.
======================================================================================================
    """,
    'author': 'OpenERP SA',
    'depends': ['project', 'portal'],
    'data': [
        'security/portal_security.xml',
        'security/ir.model.access.csv',
        'portal_project_view.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'category': 'Hidden',
}
