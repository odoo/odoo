# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Website Rating Project Issue',
    'version': '0.1',
    'category': 'Website',
    'complexity': 'easy',
    'description': """
This module display project customer satisfaction on your website.
==================================================================================================
    """,
    'depends': [
        'website_project_issue',
        'rating_project_issue'
    ],
    'data': [
        'views/website_rating_project.xml',
        'views/project_project_view.xml',
    ],
    'installable': True,
}
