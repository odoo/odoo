# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website profile',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Access the website profile of the users',
    'description': """Allows to acces the website profile of the users and see their statistics (karma, badges, etc..)""",
    'depends': [
        'website',
        'gamification'
    ],
    'data': [
        'views/gamification_badge_views.xml',
        'security/ir.model.access.csv',
    ],
    'auto_install': False,
}
