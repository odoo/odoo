# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'portal Rating',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Bridge module for rating on portal and website stuff.
        """,
    'depends': ['rating', 'portal'],
    'data': [
        'views/portal_rating_templates.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
}
