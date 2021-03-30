# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email Marketing',
    'summary': 'Design, send and track emails',
    'description': "",
    'version': '2.3',
    'sequence': 60,
    'website': 'https://www.odoo.com/page/mailing',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'contacts',
        'mail',
        'utm',
        'link_tracker',
        'web_editor',
        'web_kanban_gauge',
        'social_media',
        'web_tour',
        'digest',
    ],
    'data': [
        'security/mass_mailing_security.xml',
        'security/ir.model.access.csv',
        'data/mail_data.xml',
        'data/mailing_data_templates.xml',
        'data/mass_mailing_data.xml',
        'wizard/mail_compose_message_views.xml',
        'wizard/mailing_contact_to_list_views.xml',
        'wizard/mailing_list_merge_views.xml',
        'wizard/mailing_mailing_test_views.xml',
        'views/mailing_mailing_views_menus.xml',
        'views/mailing_trace_views.xml',
        'views/link_tracker_views.xml',
        'views/mailing_contact_views.xml',
        'views/mailing_list_views.xml',
        'views/mailing_mailing_views.xml',
        'views/res_config_settings_views.xml',
        'views/utm_campaign_views.xml',
        'report/mailing_trace_report_views.xml',
        'views/assets.xml',
        'views/mass_mailing_templates_portal.xml',
        'views/themes_templates.xml',
        'views/snippets_themes.xml',
    ],
    'demo': [
        'data/mass_mailing_demo.xml',
    ],
    'application': True,
    'assets': {
        'web.assets_backend': [
            'mass_mailing/static/src/scss/mass_mailing.scss',
            'mass_mailing/static/src/scss/mass_mailing_mobile.scss',
            'mass_mailing/static/src/css/email_template.css',
            'mass_mailing/static/src/js/mass_mailing.js',
            'mass_mailing/static/src/js/mass_mailing_widget.js',
            'mass_mailing/static/src/js/unsubscribe.js',
        ],
        'mass_mailing.assets_mail_themes': [
            'mass_mailing/static/src/scss/themes/**/*',
        ],
        'mass_mailing.assets_mail_themes_edition': [
            ('include', 'web._assets_helpers'),
            'web/static/lib/bootstrap/scss/_variables.scss',
            'mass_mailing/static/src/scss/mass_mailing.ui.scss',
            'web/static/src/scss/webclient.scss',
        ],
        'web.assets_common': [
            'mass_mailing/static/src/js/tours/**/*',
        ],
        'web.qunit_suite_tests': [
            'mass_mailing/static/tests/field_html_test.js',
            'mass_mailing/static/src/js/mass_mailing_snippets.js',
            'mass_mailing/static/tests/mass_mailing_html_tests.js',
        ],
        'web.assets_qweb': [
            'mass_mailing/static/src/xml/*.xml',
        ],
    }
}
