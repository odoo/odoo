# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Link Tracker',
    'category': 'Marketing',
    'description': """
Shorten URLs and use them to track clicks and UTMs
""",
    'version': '1.0',
    'depends': ['utm'],
    'data': [
        'views/link_tracker_views.xml',
        'security/ir.model.access.csv',
    ],
}
