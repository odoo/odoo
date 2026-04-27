# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Studio",
    'summary': "Create and customize your Odoo apps",
    'website': 'https://www.odoo.com/app/studio',
    'description': """
Studio - Customize Odoo
=======================

This addon allows the user to customize most element of the user interface, in a
simple and graphical way. It has two main features:

* create a new application (add module, top level menu item, and default action)
* customize an existing application (edit menus, actions, views, translations, ...)

Note: Only the admin user is allowed to make those customizations.
""",
    'category': 'Customizations/Studio',
    'sequence': 75,
    'version': '1.0',
    'depends': [
        'base_automation',
        'base_import_module',
        'mail',
        'web',
        'web_enterprise',
        'html_editor',
        'web_editor',
        'web_map',
        'web_gantt',
        'web_cohort',
        'sms',
    ],
    'data': [
        'views/assets.xml',
        'views/actions.xml',
        'views/ir_actions_report_xml.xml',
        'views/ir_model_data.xml',
        'views/studio_approval_views.xml',
        'views/reset_view_arch_wizard.xml',
        'views/studio_export_wizard_views.xml',
        'views/studio_export_model_views.xml',
        'data/mail_templates.xml',
        'data/mail_activity_type_data.xml',
        'data/web_tour_tour.xml',
        'wizard/base_module_uninstall_view.xml',
        'security/ir.model.access.csv',
        'security/studio_security.xml',
    ],
    'application': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'web_studio/static/src/systray_item/**/*.js',
            'web_studio/static/src/studio_service.js',
            'web_studio/static/src/utils.js',

            'web_studio/static/src/client_action/studio_action_loader.js',
            'web_studio/static/src/client_action/app_creator/app_creator_shortcut.js',
            'web_studio/static/src/client_action/components/**/*.js',
            'web_studio/static/src/client_action/components/**/*.xml',
            'web_studio/static/src/export/**/*.js',
            'web_studio/static/src/home_menu/**/*.js',
            'web_studio/static/src/views/**/*.js',
            'web_studio/static/src/js/**/*.js',
            ('remove', 'web_studio/static/src/views/kanban_report/**/*'),
            'web_studio/static/src/approval/**/*',
            'web_studio/static/src/**/*.xml',
            'web_studio/static/src/client_action/report_editor/qweb_table_plugin.scss',
        ],
        # This bundle is lazy loaded: it is loaded when studio is opened for the first time
        'web_studio.studio_assets': [
            ('include', 'web.assets_backend_lazy'),
            ('include', 'web_studio.studio_assets_minimal'),
        ],
        'web_studio.studio_assets_minimal': [
            'web_studio/static/src/client_action/**/*.js',
            'web_studio/static/src/views/kanban_report/**/*.js',
            ('remove', 'web_studio/static/src/client_action/studio_action_loader.js'),
            ('remove', 'web_studio/static/src/client_action/app_creator/app_creator_shortcut.js'),

            ('include', 'web._assets_helpers'),
            'web_studio/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            'web_studio/static/src/client_action/variables.scss',
            'web_studio/static/src/client_action/mixins.scss',
            'web_studio/static/src/client_action/**/*.scss',
            ("remove", "web_studio/static/src/client_action/report_editor/report_iframe.scss"),
            'web_studio/static/src/views/kanban_report/**/*.scss',
        ],
        "web_studio.studio_assets_dark": [
            'web_studio/static/src/client_action/variables.dark.scss',
            ('include', 'web.assets_backend_lazy_dark'),
            ('include', 'web_studio.studio_assets_minimal'),
        ],
        'web.assets_tests': [
            'web_studio/static/tests/tours/**/*',
        ],
        'web_studio.report_assets': [
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            "web/static/src/webclient/actions/reports/report.scss",
            'web_studio/static/src/client_action/report_editor/report_iframe.scss',
            'web_studio/static/src/client_action/report_editor/qweb_table_plugin.scss',
        ],
        'web.qunit_suite_tests': [
            # In tests we don't want to lazy load this
            # And we don't want to push them into any other test suite either
            # as web.tests_assets would
            ('include', 'web_studio.studio_assets_minimal'),
            'web_studio/static/tests/legacy/**/*.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web_studio/static/tests/legacy/views/disable_patch.js',
        ],
        'web.assets_unit_tests': [
            ('include', 'web_studio.studio_assets_minimal'),
            'web_studio/static/tests/**/*',
            ('remove', 'web_studio/static/tests/legacy/**/*'),
            ('remove', 'web_studio/static/tests/tours/**/*'),
        ],
    }
}
