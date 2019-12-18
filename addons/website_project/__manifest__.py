# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Project',
    'category': 'Website/Website',
    'summary': 'Publish your project ratings',
    'version': '1.0',
    'description': """
Allows to publish all ratings for a particular project.""",
    'depends': ['website', 'project'],
    'data': [
        'views/project_rating_templates.xml',
        'views/project_project_views.xml',
    ],
    'installable': True,
    'auto_install': True,
}
