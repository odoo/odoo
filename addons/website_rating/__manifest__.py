# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Rating',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Bridge module for rating on website stuff.
        """,
    'depends': ['rating', 'website_mail'],
    'data': [
        'views/assets.xml',
        'views/rating_views.xml',
        'views/portal_templates.xml',
        'views/rating_templates.xml',
    ],
    'auto_install': True,
}
