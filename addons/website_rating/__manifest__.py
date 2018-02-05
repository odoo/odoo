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
        'views/website_rating_templates.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
