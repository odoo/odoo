# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Customer Portal',
    'summary': 'Customer Portal',
    'sequence': 9000,
    'category': 'Hidden',
    'description': """
This module adds required base code for a fully integrated customer portal.
It contains the base controller class and base templates. Business addons
will add their specific templates and controllers to extend the customer
portal.

This module contains most code coming from odoo v10 website_portal. Purpose
of this module is to allow the display of a customer portal without having
a dependency towards website editing and customization capabilities.""",
    'depends': ['web', 'web_editor', 'http_routing', 'mail', 'auth_signup'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/mail_templates.xml',
        'views/mail_templates_public.xml',
        'views/portal_templates.xml',
        'views/res_config_settings_views.xml',
        'wizard/portal_share_views.xml',
        'wizard/portal_wizard_views.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'portal/static/src/scss/primary_variables.scss',
        ],
        'web._assets_frontend_helpers': [
            ('prepend', 'portal/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_backend': [
            'portal/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'portal/static/src/scss/portal.scss',
            'portal/static/src/js/portal.js',
            'portal/static/src/xml/portal_chatter.xml',
            'portal/static/src/js/portal_composer.js',
            'portal/static/src/js/portal_security.js',
            'portal/static/src/js/portal_signature.js',
            'portal/static/src/xml/portal_signature.xml',
            'portal/static/src/js/portal_sidebar.js',
            'portal/static/src/xml/portal_security.xml',
            'portal/static/src/js/components/**/*',

            'web/static/src/views/view_dialogs/form_view_dialog.js',
            'web/static/src/core/debug/*',
            'web/static/src/core/commands/*',
            'web/static/src/model/**/*',
            'web/static/src/search/**/*',
            'web/static/src/views/view.js',
            'web/static/src/views/view_hook.js',
            'web/static/src/views/onboarding_banner.js',
            'web/static/src/webclient/actions/action_service.js',
            'web/static/src/webclient/actions/action_hook.js',
            'web/static/src/webclient/actions/action_dialog.js',
            'web/static/src/webclient/actions/reports/utils.js',
            'web/static/src/webclient/actions/reports/report_action.js',
            'web/static/src/webclient/actions/reports/report_hook.js',
            'web/static/src/views/utils.js',
            'web/static/src/views/fields/formatters.js',
            'web/static/src/views/fields/file_handler.*',

            'mail/static/src/core/common/**/*',
            'mail/static/src/js/utils.js',
            'mail/static/src/utils/common/**/*',
            'mail/static/src/chatter/web_portal/**/*',
            'mail/static/src/chatter/portal/**/*',
            'mail/static/src/discuss/typing/**/*',
            'mail/static/src/discuss/core/common/action_panel.*',
            'portal/static/src/embed/core/**/*',
            'portal/static/src/embed/chatter/**/*',
            'portal/static/src/embed/frontend/**/*',
        ],
        'web.assets_tests': [
            'portal/static/tests/**/*',
        ],
        'portal.assets_chatter': [
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            ('include', 'web._assets_bootstrap_backend'),
            'web/static/src/webclient/webclient.scss',
            'web/static/src/core/avatar/avatar.scss',
            'mail/static/src/core/common/**/*',
            'mail/static/src/utils/common/**/*',
            ('remove', 'mail/static/src/**/*.dark.scss'),
            'mail/static/src/chatter/web_portal/chatter.scss',
            'portal/static/src/embed/scss/shadow.scss',
        ],
    },
    'license': 'LGPL-3',
}
