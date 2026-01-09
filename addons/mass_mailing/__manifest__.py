# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Email Marketing',
    'summary': 'Design, send and track emails',
    'version': '2.7',
    'sequence': 60,
    'website': 'https://www.odoo.com/app/email-marketing',
    'category': 'Marketing/Email Marketing',
    'depends': [
        'contacts',
        'mail',
        'html_builder',
        'utm',
        'link_tracker',
        'social_media',
        'web_tour',
        'digest',
    ],
    'data': [
        'data/res_groups_privilege_data.xml',
        'security/res_groups_data.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/digest_data.xml',
        'data/ir_attachment_data.xml',
        'data/ir_config_parameter_data.xml',
        'data/ir_cron_data.xml',
        'data/mailing_data_templates.xml',
        'data/mailing_list_contact.xml',
        'data/mailing_subscription_optout.xml',
        'data/mailing_subscription.xml',
        'data/mass_mailing_tour.xml',
        'wizard/mail_compose_message_views.xml',
        'wizard/mailing_contact_import_views.xml',
        'wizard/mailing_contact_to_list_views.xml',
        'wizard/mailing_list_merge_views.xml',
        'wizard/mailing_mailing_test_views.xml',
        'wizard/mailing_mailing_schedule_date_views.xml',
        'report/mailing_trace_report_views.xml',
        'views/mail_blacklist_views.xml',
        'views/mailing_filter_views.xml',
        'views/mailing_mobile_preview_content.xml',
        'views/mailing_trace_views.xml',
        'views/link_tracker_views.xml',
        'views/mailing_contact_views.xml',
        'views/mailing_list_views.xml',
        'views/mailing_mailing_views.xml',
        'views/mailing_subscription_optout_views.xml',
        'views/mailing_subscription_views.xml',
        'views/res_config_settings_views.xml',
        'views/utm_campaign_views.xml',
        'views/mailing_menus.xml',
        'views/mailing_templates_portal_layouts.xml',
        'views/mailing_templates_portal_management.xml',
        'views/mailing_templates_portal_unsubscribe.xml',
        'views/themes_templates.xml',
        'views/snippets_themes.xml',
        'views/snippets/mass_mailing_columns_snippets.xml',
        'views/snippets/mass_mailing_footer_snippets.xml',
        'views/snippets/mass_mailing_headers_snippets.xml',
        'views/snippets/mass_mailing_headings_snippets.xml',
        'views/snippets/mass_mailing_images_snippets.xml',
        'views/snippets/mass_mailing_inner_snippets.xml',
        'views/snippets/mass_mailing_marketing_snippets.xml',
        'views/snippets/mass_mailing_masonry_snippets.xml',
        'views/snippets/mass_mailing_people_snippets.xml',
        'views/snippets/mass_mailing_text_snippets.xml',
        'views/snippets/mass_mailing_website_snippets.xml',
    ],
    'demo': [
        'demo/utm.xml',
        'demo/mailing_list_contact.xml',
        'demo/mailing_subscription.xml',
        'demo/mailing_mailing.xml',
        'demo/mailing_trace.xml',
        'demo/res_users.xml',
    ],
    'application': True,
    'assets': {
        'mass_mailing.assets_builder': [
            # lazy builder assets NOT applied in iframe
            ('include', 'html_builder.assets'),
            ('remove', 'web/static/fonts/fonts.scss'),
            'mass_mailing/static/src/builder/**/*',
        ],
        'mass_mailing.assets_iframe_style': [
            # minimal style assets required to view the mail content
            # convert_inline ONLY uses this and inline styles.

            # useful scss from /web web.assets_frontend
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/bootstrap_overridden.scss',
            ('include', 'web._assets_frontend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            'web/static/lib/bootstrap/scss/_alert.scss',
            ('include', 'web._assets_bootstrap_frontend'),

            # useful scss from /html_editor web.assets_frontend
            # TODO EGGMAIL: could improve load time by splitting scss from JS files
            ('include', 'html_editor.assets_media_dialog'),
            ('include', 'html_editor.assets_readonly'),
            'html_editor/static/src/public/**/*',
            'html_editor/static/src/scss/html_editor.common.scss',
            'html_editor/static/src/scss/html_editor.frontend.scss',
            'html_editor/static/src/scss/base_style.scss',

            ('after', 'web/static/lib/bootstrap/scss/_maps.scss', 'mass_mailing/static/src/scss/mass_mailing.ui.scss'),

            'html_editor/static/src/scss/bootstrap_overridden.scss',
            'html_builder/static/src/scss/background.scss',

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/src/scss/animation.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/scss/fontawesome_overridden.scss',

            ('include', 'mass_mailing.assets_mail_themes'),
            'mass_mailing/static/src/scss/mass_mailing_mail.scss',
            'mass_mailing/static/src/iframe_assets/**/*',
        ],
        # style assets used to view the mail content in Odoo, but not used
        # during html conversion, specific to the builder
        'mass_mailing.assets_inside_builder_iframe': [
            ('include', 'html_builder.assets_inside_builder_iframe'),
            # TODO ABD: fix bundles usages so that html_editor files don't
            # have to be cherry picked individually.
            'html_editor/static/src/main/selection_placeholder_plugin.scss',
            'mass_mailing/static/src/builder/**/*.inside.scss'
        ],
        'mass_mailing.iframe_add_dialog': [
            'mass_mailing/static/src/builder/snippet_viewer/*.scss',
        ],
        'mass_mailing.mailing_assets': [
            'mass_mailing/static/src/scss/mailing_portal.scss',
            'mass_mailing/static/src/interactions/subscribe.js',
            'mass_mailing/static/src/xml/mailing_portal_subscription_blocklist.xml',
            'mass_mailing/static/src/xml/mailing_portal_subscription_feedback.xml',
            'mass_mailing/static/src/xml/mailing_portal_subscription_form.xml',
        ],
        'web.assets_backend': [
            'mass_mailing/static/src/editor/**/*',
            'mass_mailing/static/src/fields/**/*',
            'mass_mailing/static/src/themes/**/*',
            'mass_mailing/static/src/iframe/**/*',
            'mass_mailing/static/src/scss/mailing_filter_widget.scss',
            'mass_mailing/static/src/scss/mass_mailing.scss',
            'mass_mailing/static/src/scss/mass_mailing_mobile.scss',
            'mass_mailing/static/src/scss/mass_mailing_mobile_preview.scss',
            'mass_mailing/static/src/js/mailing_m2o_filter.js',
            'mass_mailing/static/src/xml/mailing_filter_widget.xml',
            'mass_mailing/static/src/js/tours/**/*',
        ],
        'web.assets_backend_lazy': [
            'mass_mailing/static/src/views/mass_mailing_subscription_graph_renderer.js',
        ],
        'mass_mailing.assets_mail_themes': [
            'mass_mailing/static/src/scss/themes/**/*',
        ],
        'web.assets_frontend': [
            'mass_mailing/static/src/js/tours/**/*',
        ],
        'web.assets_tests': [
            'mass_mailing/static/tests/tours/**/*',
        ],
        'web.assets_unit_tests': [
            ('include', 'mass_mailing.assets_builder'),
            'mass_mailing/static/tests/mass_mailing_favourite_filter.test.js',
            'mass_mailing/static/tests/mass_mailing_html_field.test.js',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
