# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website profile',
    'category': 'Website/Website',
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
        'security/ir.access.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_profile/static/src/scss/website_profile.scss',
            'website_profile/static/src/interactions/**/*',
            ('remove', 'website_profile/static/src/interactions/**/*.edit.js'),
        ],
        # Lazy loaded on the frontend, after html_editor.assets_editor_frontend
        'website_profile.assets_html_editor': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            'web/static/src/views/fields/file_handler.*',
            'website_profile/static/src/components/**/*',
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
