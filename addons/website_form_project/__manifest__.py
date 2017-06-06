# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Form - Project',
    'category': 'Project',
    'summary': 'Create Tasks From Contact Form',
    'version': '1.0',
    'description': """
Odoo Contact Form
=================

        """,
    'depends': ['website_form', 'project'],
    'data': [
        'data/website_form_project_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}
