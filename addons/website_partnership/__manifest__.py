# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Partnership',
    'category': 'Website/Website',
    'summary': 'Publish your partners on your website',
    'description': """
This module allows to publish your members/partners on your website.

To publish a member, set a *Level* in their contact form and click the *Publish* button.
    """,
    'depends': ['partnership', 'website_partner'],
    'data': [
        'views/res_partner_grade_views.xml',
        'views/website_partnership_templates.xml',
        'views/res_config_settings_views.xml',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/res_partner_grade_demo.xml',
        'demo/res_partner_demo.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'website_partnership/static/src/scss/primary_variable.scss',
        ],
        'web.assets_frontend': [
            'website_partnership/static/src/scss/website_partnership.scss',
        ],
        'website.website_builder_assets': [
            'website_partnership/static/src/website_builder/**/*',
        ],
        'web.assets_tests': [
            'website_partnership/static/tests/tours/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
