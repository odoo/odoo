# -*- coding: utf-8 -*-
{
    'name': 'Project Rating',
    'version': '1.0',
    'category': 'Project',
    'description': """
This module Allows a customer to give rating on Project.
""",
    'website': 'http://odoo.com',
    'depends': [
        'rating',
        'project'
    ],
    'data': [
        'data/project_data.xml',
        'views/project_view.xml',
        'views/project_dashboard.xml',
    ],
    'demo': ['data/project_demo.xml'],
    'installable': True,
}
