# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email Marketing Egg',
    'summary': 'Design, send and track emails',
    'version': '1.0',
    'sequence': 61,
    'website': 'https://www.odoo.com/app/email-marketing',
    'category': 'Hidden',
    'auto_install': True,
    'depends': [
        'mass_mailing',
        'html_builder',
        'html_editor',
    ],
    'data': [
        'views/mailing_mailing_views.xml'
    ],
    'assets': {
        'mass_mailing_egg.assets_builder': [  # equivalent html_builder.assets in website_builder_action.xml
            # lazy builder assets NOT applied in iframe
            ('include', 'html_builder.assets'),
            'mass_mailing_egg/static/src/html_builder/**/*',
        ],
        # TODO EGGMAIL: evaluate if necessary to have interactions for mass_mailing
        # 'mass_mailing_egg.assets_iframe_core': [  # web.assets_frontend lite, minimal env to spawn interactions
        #     # minimal JS assets required to view the mail content
        # ],
        'mass_mailing_egg.assets_iframe_style': [  # equivalent website.inside_builder_style in website_builder_action.js
            # minimal style assets required to view the mail content
            # convert_inline ONLY uses this and inline styles.
        ],
        # 'mass_mailing_egg.assets_iframe_edit': [  # equivalent html_builder.assets_edit_frontend in website_builder_action.js
        #     # JS and style assets required to edit the mail content
        # ],
        'mass_mailing_egg.assets_iframe_dark': [  # separated complement of assets_iframe_style for dark mode
            # style assets for dark mode. Not used by convert_inline.
            # TODO EGGMAIL: investigate how this can behave properly with convert_inline (i.e. user chooses pretty colors for
            # dark mode, but these colors are not pretty when the dark mode is not there anymore after sending the mail).
        ],
        'web.assets_backend': [
            'mass_mailing_egg/static/src/interaction_service/**/*',
            'mass_mailing_egg/static/src/fields/**/*',
            'mass_mailing_egg/static/src/theme_selector/**/*',
        ],
        'web.assets_unit_tests': [
            # 'mass_mailing_egg/static/tests/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
