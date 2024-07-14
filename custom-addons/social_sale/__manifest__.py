# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale statistics on social',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Add sale UTM info on social',
    'description': """UTM and post on sale orders""",
    'depends': ['social', 'sale'],
    'data': [
        'views/social_post_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}
