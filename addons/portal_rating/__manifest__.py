# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Portal Rating',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Bridge module for rating on portal and website  stuff.
        """,
    'depends': ['rating'],
    'data': [
        'views/portal_rating_templates.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
