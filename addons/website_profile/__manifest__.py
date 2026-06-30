# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website profile',
    'category': 'Website/Website',
    'version': '1.0',
    'summary': 'Access the website profile of the users',
    'description': "Allows to access the website profile of the users and see their statistics (karma, badges, etc..)",
    'depends': [
        'html_editor',
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
            'web/static/src/views/fields/file_handler.*',
            'website_profile/static/src/scss/website_profile.scss',
            'website_profile/static/src/components/**/*',
            'website_profile/static/src/interactions/**/*',
            ('remove', 'website_profile/static/src/interactions/**/*.edit.js'),
            ('include', 'html_editor.assets_editor'),
        ],
        'website.assets_inside_builder_iframe': [
            'website_profile/static/src/**/*.edit.js',
        ],
        'web.assets_tests': [
            'website_profile/static/tests/tours/tour_website_profile_description.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
