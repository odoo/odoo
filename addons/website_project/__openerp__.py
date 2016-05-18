# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Website Project",
    'description': """
This module app will allow portal user(s) to see their tasks under 'My Account' menu in front end
==============================================================================================
    """,
    'category': 'Website',

    'depends': ['project', 'website_portal'],
    'data': [
        'security/project_security.xml',
        'views/project_views.xml',
        'views/website_project_templates.xml',
    ],
    'demo': [
        'demo/project_demo.xml',
    ],
}
