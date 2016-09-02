# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Issues Form',
    'category': 'Project',
    'summary': 'Create Issues From Contact Form',
    'version': '1.0',
    'description': """
Odoo Contact Form
====================

        """,
    'depends': ['website_form', 'project_issue'],
    'data': [
        'data/website_issue_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
