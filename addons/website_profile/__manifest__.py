# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website profile',
    'category': 'Hidden',
    'version': '1.0',
    'summary': 'Access the website profile of the users',
    'description': "Allows to access the website profile of the users and see their statistics (karma, badges, etc..)",
    'depends': [
        'website_partner',
        'gamification'
    ],
    'data': [
        'data/mail_template_data.xml',
        'views/gamification_badge_views.xml',
        'views/website_profile.xml',
        'views/website_views.xml',
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_profile/static/src/scss/website_profile.scss',
            'website_profile/static/src/js/website_profile.js',
        ],
    },
    'license': 'LGPL-3',
}
