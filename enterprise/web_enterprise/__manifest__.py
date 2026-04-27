# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Enterprise',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Enterprise Web Client.
===========================

This module modifies the web addon to provide Enterprise design and responsiveness.
        """,
    'depends': ['web', 'base_setup'],
    'auto_install': ['web'],
    'data': [
        'views/webclient_templates.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('after', 'web/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/**/*.variables.scss'),
            ('before', 'web/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('before', 'web/static/src/scss/secondary_variables.scss', 'web_enterprise/static/src/scss/secondary_variables.scss'),
        ],
        'web._assets_backend_helpers': [
            ('before', 'web/static/src/scss/bootstrap_overridden.scss', 'web_enterprise/static/src/scss/bootstrap_overridden.scss'),
        ],
        'web.assets_frontend': [
            'web_enterprise/static/src/webclient/home_menu/home_menu_background.scss', # used by login page
            'web_enterprise/static/src/webclient/navbar/navbar.scss',
        ],
        'web.assets_backend': [
            'web_enterprise/static/src/webclient/**/*.scss',
            'web_enterprise/static/src/views/**/*.scss',

            'web_enterprise/static/src/core/**/*',
            'web_enterprise/static/src/webclient/**/*.js',
            ('after', 'web/static/src/views/list/list_renderer.xml', 'web_enterprise/static/src/views/list/list_renderer_desktop.xml'),
            'web_enterprise/static/src/webclient/**/*.xml',
            'web_enterprise/static/src/views/**/*.js',
            'web_enterprise/static/src/views/**/*.xml',
            ('remove', 'web_enterprise/static/src/views/pivot/**'),

            # Don't include dark mode files in light mode
            ('remove', 'web_enterprise/static/src/**/*.dark.scss'),
        ],
        'web.assets_backend_lazy': [
            'web_enterprise/static/src/views/pivot/**',
        ],
        'web.assets_backend_lazy_dark': [
            ('include', 'web.dark_mode_variables'),
            # web._assets_backend_helpers
            ('before', 'web_enterprise/static/src/scss/bootstrap_overridden.scss', 'web_enterprise/static/src/scss/bootstrap_overridden.dark.scss'),
            ('after', 'web/static/lib/bootstrap/scss/_functions.scss', 'web_enterprise/static/src/scss/bs_functions_overridden.dark.scss'),
        ],
        'web.assets_web': [
            ('replace', 'web/static/src/main.js', 'web_enterprise/static/src/main.js'),
        ],
        # ========= Dark Mode =========
        "web.dark_mode_variables": [
            # web._assets_primary_variables
            ('before', 'web_enterprise/static/src/scss/primary_variables.scss', 'web_enterprise/static/src/scss/primary_variables.dark.scss'),
            ('before', 'web_enterprise/static/src/**/*.variables.scss', 'web_enterprise/static/src/**/*.variables.dark.scss'),
            # web._assets_secondary_variables
            ('before', 'web_enterprise/static/src/scss/secondary_variables.scss', 'web_enterprise/static/src/scss/secondary_variables.dark.scss'),
        ],
        "web.assets_web_dark": [
            ('include', 'web.dark_mode_variables'),
            # web._assets_backend_helpers
            ('before', 'web_enterprise/static/src/scss/bootstrap_overridden.scss', 'web_enterprise/static/src/scss/bootstrap_overridden.dark.scss'),
            ('after', 'web/static/lib/bootstrap/scss/_functions.scss', 'web_enterprise/static/src/scss/bs_functions_overridden.dark.scss'),
            # assets_backend
            'web_enterprise/static/src/**/*.dark.scss',
        ],
        'web.tests_assets': [
            'web_enterprise/static/tests/*.js',
        ],
        "web.assets_tests": [
            "web_enterprise/static/tests/tours/**/*.js",
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'web_enterprise/static/tests/**/*.test.js',
        ],
        'web.qunit_suite_tests': [
            'web_enterprise/static/tests/views/**/*.js',
            'web_enterprise/static/tests/webclient/**/*.js',
            ('remove', 'web_enterprise/static/tests/**/*.test.js'),
        ],
    },
    'license': 'OEEL-1',
}
