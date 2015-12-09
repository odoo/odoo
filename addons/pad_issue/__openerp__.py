# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Pad on issues',
    'version': '1.0',
    'category': 'Project Management',
    'description': """
This module adds a PAD in all issues form views.
================================================
    """,
    'website': 'https://www.odoo.com/page/project-management',
    'depends': ['project_issue', 'pad'],
    'data': ['project_issue.xml'],
    'demo': [],
    'installable': True,
    'auto_install': True,
}
