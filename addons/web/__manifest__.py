# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
Odoo Web core module.
========================

This module provides the core of the Odoo Web Client.
""",
    'depends': ['base'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/webclient_templates.xml',
        'views/report_templates.xml',
        'views/base_document_layout_views.xml',
        'views/partner_view.xml',
        'views/speedscope_template.xml',
        'views/neutralize_views.xml',
        'data/ir_attachment.xml',
        'data/report_layout.xml',
    ],
    'assets': {
        # ---------------------------------------------------------------------
        # MAIN BUNDLES
        # ---------------------------------------------------------------------
        # These are the bundles meant to be called via "t-call-assets" in
        # regular XML templates.
        #
        # The convention to name bundles is as following:
        # 1) the name of the first module defining the bundle
        # 2) the prefix "assets_"
        # 3) an arbitrary name, relevant to the content of the bundle.
        #
        # Examples:
        #   > web_editor.assets_snippets_menu = assets needed by components defined in the "web_editor" module.

        'web.assets_emoji': [
            'web/static/src/core/emoji_picker/emoji_data.js'
        ],
        'web.assets_backend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            ('include', 'web._assets_bootstrap_backend'),

            ('include', 'web._assets_core'),

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/scss/animation.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/views/fields/translation_dialog.scss',
            'web/static/src/legacy/scss/ui.scss',

            'web/static/src/polyfills/clipboard.js',

            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/dist/util/index.js',
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/util/config.js',
            'web/static/lib/bootstrap/js/dist/util/component-functions.js',
            'web/static/lib/bootstrap/js/dist/util/backdrop.js',
            'web/static/lib/bootstrap/js/dist/util/focustrap.js',
            'web/static/lib/bootstrap/js/dist/util/sanitizer.js',
            'web/static/lib/bootstrap/js/dist/util/scrollbar.js',
            'web/static/lib/bootstrap/js/dist/util/swipe.js',
            'web/static/lib/bootstrap/js/dist/util/template-factory.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            'web/static/lib/bootstrap/js/dist/alert.js',
            'web/static/lib/bootstrap/js/dist/button.js',
            'web/static/lib/bootstrap/js/dist/carousel.js',
            'web/static/lib/bootstrap/js/dist/collapse.js',
            'web/static/lib/bootstrap/js/dist/dropdown.js',
            'web/static/lib/bootstrap/js/dist/modal.js',
            'web/static/lib/bootstrap/js/dist/offcanvas.js',
            'web/static/lib/bootstrap/js/dist/tooltip.js',
            'web/static/lib/bootstrap/js/dist/popover.js',
            'web/static/lib/bootstrap/js/dist/scrollspy.js',
            'web/static/lib/bootstrap/js/dist/tab.js',
            'web/static/lib/bootstrap/js/dist/toast.js',
            'web/static/src/libs/bootstrap.js',

            'web/static/lib/dompurify/DOMpurify.js',

            'base/static/src/css/modules.css',

            'web/static/src/core/utils/transitions.scss',
            'web/static/src/model/**/*',
            'web/static/src/search/**/*',
            'web/static/src/webclient/icons.scss', # variables required in list_controller.scss
            'web/static/src/views/**/*',
            ('remove', 'web/static/src/views/graph/**'),
            ('remove', 'web/static/src/views/pivot/**'),

            'web/static/src/webclient/**/*',
            ('remove', 'web/static/src/webclient/clickbot/clickbot.js'), # lazy loaded
            ('remove', 'web/static/src/views/form/button_box/*.scss'),

            # remove the report code and whitelist only what's needed
            ('remove', 'web/static/src/webclient/actions/reports/**/*'),
            'web/static/src/webclient/actions/reports/*.js',
            'web/static/src/webclient/actions/reports/*.xml',

            'web/static/src/libs/pdfjs.js',

            'web/static/src/scss/ace.scss',
            'web/static/src/scss/base_document_layout.scss',

            'web/static/src/legacy/scss/dropdown.scss',
            'web/static/src/legacy/scss/fields.scss',
            'base/static/src/scss/res_partner.scss',

            # Form style should be computed before
            'web/static/src/views/form/button_box/*.scss',

            # Don't include dark mode files in light mode
            ('remove', 'web/static/src/**/*.dark.scss'),
        ],
        'web.assets_backend_lazy': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',

            'web/static/src/views/graph/**',
            'web/static/src/views/pivot/**',
        ],
        'web.assets_backend_lazy_dark': [
            ('include', 'web.assets_backend_lazy'),
        ],
        'web.assets_web': [
            ('include', 'web.assets_backend'),
            'web/static/src/main.js',
            'web/static/src/start.js',
        ],
        'web.assets_frontend_minimal': [
            'web/static/src/polyfills/object.js',
            'web/static/src/polyfills/array.js',
            'web/static/src/module_loader.js',
            'web/static/src/session.js',
            'web/static/src/core/browser/cookie.js',
            'web/static/src/core/utils/ui.js',
            'web/static/src/legacy/js/public/minimal_dom.js',
            'web/static/src/legacy/js/public/lazyloader.js',
        ],
        'web.assets_frontend': [
            # TODO the 'assets_frontend' bundle now includes 'assets_common'
            # files directly. That work was however a good opportunity to start
            # removing the files that are not needed anymore in frontend layouts
            # but it was not done: all common files were simply put in this
            # bundle. We'll have to optimize that.

            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',
            'web/static/lib/luxon/luxon.js',

            ('include', 'web._assets_bootstrap_frontend'),

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/scss/animation.scss',
            'web/static/src/scss/base_frontend.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/views/fields/translation_dialog.scss',
            'web/static/src/views/fields/signature/signature_field.scss',

            'web/static/src/legacy/scss/ui.scss',

            ('include', 'web.assets_frontend_minimal'),

            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/dist/util/index.js',
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/util/config.js',
            'web/static/lib/bootstrap/js/dist/util/component-functions.js',
            'web/static/lib/bootstrap/js/dist/util/backdrop.js',
            'web/static/lib/bootstrap/js/dist/util/focustrap.js',
            'web/static/lib/bootstrap/js/dist/util/sanitizer.js',
            'web/static/lib/bootstrap/js/dist/util/scrollbar.js',
            'web/static/lib/bootstrap/js/dist/util/swipe.js',
            'web/static/lib/bootstrap/js/dist/util/template-factory.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            'web/static/lib/bootstrap/js/dist/alert.js',
            'web/static/lib/bootstrap/js/dist/button.js',
            'web/static/lib/bootstrap/js/dist/carousel.js',
            'web/static/lib/bootstrap/js/dist/collapse.js',
            'web/static/lib/bootstrap/js/dist/dropdown.js',
            'web/static/lib/bootstrap/js/dist/modal.js',
            'web/static/lib/bootstrap/js/dist/offcanvas.js',
            'web/static/lib/bootstrap/js/dist/tooltip.js',
            'web/static/lib/bootstrap/js/dist/popover.js',
            'web/static/lib/bootstrap/js/dist/scrollspy.js',
            'web/static/lib/bootstrap/js/dist/tab.js',
            'web/static/lib/bootstrap/js/dist/toast.js',
            'web/static/src/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web/static/src/legacy/js/core/class.js',

            'web/static/src/env.js',
            'web/static/src/core/utils/transitions.scss',  # included early because used by other files
            'web/static/src/core/**/*',  # Note that 'web/static/src/core/utils/ui.js' is included in assets_frontend_minimal already
            ('remove', 'web/static/src/core/commands/**/*'),
            ('remove', 'web/static/src/core/debug/debug_menu.js'),
            ('remove', 'web/static/src/core/file_viewer/file_viewer.dark.scss'),
            ('remove', 'web/static/src/core/emoji_picker/emoji_data.js'),
            'web/static/src/core/commands/default_providers.js',
            'web/static/src/core/commands/command_palette.js',
            'web/static/src/public/error_notifications.js',
            'web/static/src/public/public_component_service.js',
            'web/static/src/public/datetime_picker_widget.js',
            'web/static/src/libs/pdfjs.js',

            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/public_root_instance.js',
            'web/static/src/legacy/js/public/public_widget.js',
            'web/static/src/legacy/js/public/signin.js',

        ],
        'web.assets_frontend_lazy': [
            ('include', 'web.assets_frontend'),
            # Remove assets_frontend_minimal
            ('remove', 'web/static/src/module_loader.js'),
            ('remove', 'web/static/src/session.js'),
            ('remove', 'web/static/src/core/browser/cookie.js'),
            ('remove', 'web/static/src/core/utils/ui.js'),
            ('remove', 'web/static/src/legacy/js/public/minimal_dom.js'),
            ('remove', 'web/static/src/legacy/js/public/lazyloader.js'),
        ],
        'web.report_assets_common': [
            # Include some helpers early to define $enable-rfs before
            # _mixin file and use primary_variables in bs_overridden_report
            'web/static/src/scss/functions.scss',
            'web/static/src/scss/utils.scss',
            ('include', 'web._assets_primary_variables'),
            ('include', 'web._assets_secondary_variables'),

            'web/static/src/webclient/actions/reports/bootstrap_overridden_report.scss',
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
            'web/static/lib/bootstrap/scss/_variables-dark.scss',
            'web/static/lib/bootstrap/scss/_maps.scss',

            ('include', 'web._assets_bootstrap_backend'),
            ('remove', 'web/static/src/scss/utilities_custom_backend.scss'),
            ('remove', 'web/static/src/scss/bootstrap_review_backend.scss'),
            ('after', 'web/static/src/scss/utilities_custom.scss', 'web/static/src/webclient/actions/reports/utilities_custom_report.scss'),

            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/dist/util/index.js',
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
            'web/static/lib/bootstrap/js/dist/util/config.js',
            'web/static/lib/bootstrap/js/dist/util/component-functions.js',
            'web/static/lib/bootstrap/js/dist/util/backdrop.js',
            'web/static/lib/bootstrap/js/dist/util/focustrap.js',
            'web/static/lib/bootstrap/js/dist/util/sanitizer.js',
            'web/static/lib/bootstrap/js/dist/util/scrollbar.js',
            'web/static/lib/bootstrap/js/dist/util/swipe.js',
            'web/static/lib/bootstrap/js/dist/util/template-factory.js',
            'web/static/lib/bootstrap/js/dist/base-component.js',
            'web/static/lib/bootstrap/js/dist/alert.js',
            'web/static/lib/bootstrap/js/dist/button.js',
            'web/static/lib/bootstrap/js/dist/carousel.js',
            'web/static/lib/bootstrap/js/dist/collapse.js',
            'web/static/lib/bootstrap/js/dist/dropdown.js',
            'web/static/lib/bootstrap/js/dist/modal.js',
            'web/static/lib/bootstrap/js/dist/offcanvas.js',
            'web/static/lib/bootstrap/js/dist/tooltip.js',
            'web/static/lib/bootstrap/js/dist/popover.js',
            'web/static/lib/bootstrap/js/dist/scrollspy.js',
            'web/static/lib/bootstrap/js/dist/tab.js',
            'web/static/lib/bootstrap/js/dist/toast.js',

            'base/static/src/css/description.css',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/fonts/fonts.scss',

            'web/static/src/webclient/actions/reports/bootstrap_review_report.scss',
            'web/static/src/webclient/actions/reports/report.scss',
            'web/static/src/webclient/actions/reports/report_tables.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_*.scss',
            'web/static/asset_styles_company_report.scss',
        ],
        'web.report_assets_pdf': [
            'web/static/src/webclient/actions/reports/reset.min.css',
        ],

        'web.ace_lib': [
            "web/static/lib/ace/ace.js",
            "web/static/lib/ace/mode-javascript.js",
            "web/static/lib/ace/mode-xml.js",
            "web/static/lib/ace/mode-qweb.js",
            "web/static/lib/ace/mode-python.js",
            "web/static/lib/ace/mode-scss.js",
            "web/static/lib/ace/theme-monokai.js",
        ],

        # ---------------------------------------------------------------------
        # "DIRECT PRINT" BUNDLE
        # ---------------------------------------------------------------------
        "web.assets_web_print": [
            'web/static/src/scss/functions.scss',
            'web/static/src/scss/primary_variables_print.scss',

            'web/static/src/**/*.print_variables.scss',
            ('include', 'web.assets_backend'),
        ],

        # ---------------------------------------------------------------------
        # COLOR SCHEME BUNDLES
        # ---------------------------------------------------------------------
        "web.assets_web_dark": [
            ('include', 'web.assets_web'),
            'web/static/src/**/*.dark.scss',
        ],

        # ---------------------------------------------------------------------
        # SUB BUNDLES
        # ---------------------------------------------------------------------
        # These bundles can be used by main bundles but are not supposed to be
        # called directly from XML templates.
        #
        # Their naming conventions are similar to those of the main bundles,
        # with the addition of a prefixed underscore to reflect the "private"
        # aspect.

        # Bare javascript essentials: module loader, core folder and core libs
        'web._assets_core': [
            # module loader
            'web/static/src/module_loader.js',
            # libs
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            # core
            'web/static/src/env.js',
            'web/static/src/session.js',
            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/**/*',
            ('remove', 'web/static/src/core/emoji_picker/emoji_data.js'), # always lazy-loaded
        ],
        'web._assets_primary_variables': [
            'web/static/src/scss/primary_variables.scss',
            'web/static/src/**/*.variables.scss',
        ],
        'web._assets_secondary_variables': [
            'web/static/src/scss/secondary_variables.scss',
        ],
        'web._assets_helpers': [
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_mixins.scss',
            'web/static/src/scss/functions.scss',
            'web/static/src/scss/mixins_forwardport.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/src/scss/utils.scss',

            ('include', 'web._assets_primary_variables'),
            ('include', 'web._assets_secondary_variables'),
        ],
        'web._assets_jquery': [
            'web/static/lib/jquery/jquery.js',
            'web/static/src/legacy/js/libs/jquery.js',
        ],
        'web._assets_bootstrap': [
            'web/static/src/scss/import_bootstrap.scss',
            'web/static/src/scss/utilities_custom.scss',
            'web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/scss/bootstrap_review.scss',
        ],
        'web._assets_bootstrap_backend': [
            ('include', 'web._assets_bootstrap'),
            ('after', 'web/static/src/scss/utilities_custom.scss', 'web/static/src/scss/utilities_custom_backend.scss'),
            'web/static/src/scss/bootstrap_review_backend.scss',
        ],
        'web._assets_bootstrap_frontend': [
            ('include', 'web._assets_bootstrap'),
            'web/static/src/scss/bootstrap_review_frontend.scss',
        ],
        'web._assets_backend_helpers': [
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/bs_mixins_overrides_backend.scss',
        ],
        'web._assets_frontend_helpers': [
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
        ],

        # ---------------------------------------------------------------------
        # TESTS BUNDLES
        # ---------------------------------------------------------------------

        'web.assets_tests': [
            # the bundle "assets_tests" is first called in web.
            'web/static/tests/legacy/helpers/cleanup.js',
            'web/static/tests/legacy/helpers/utils.js',
            'web/static/tests/legacy/utils.js',
            'web/static/tests/tours/**/*'
        ],
        'web.__assets_tests_call__': [
            'web/static/tests/legacy/ignore_missing_deps_start.js',
            ('include', 'web.assets_tests'),
            'web/static/tests/legacy/ignore_missing_deps_stop.js',
        ],
        # Assets for test framework and setup
        'web.assets_unit_tests_setup': [
            'web/static/src/module_loader.js',

            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',

            'web/static/lib/hoot/**/*',
            'web/static/lib/hoot-dom/**/*',
            ('remove', 'web/static/lib/hoot/ui/hoot_style.css'),
            ('remove', 'web/static/lib/hoot/tests/**/*'),

            # Odoo mocks
            # ! must be loaded before other @web assets
            'web/static/tests/_framework/mock_module_loader.js',

            # Assets for features to test (views, services, fields, ...)
            # Typically includes most files in 'web.web.assets_backend'
            ('include', 'web.assets_backend'),
            ('include', 'web.assets_backend_lazy'),

            'web/static/src/public/public_component_service.js',
            'web/static/src/webclient/clickbot/clickbot.js',
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'web/static/tests/**/*',

            ('remove', 'web/static/tests/_framework/mock_module_loader.js'),
            ('remove', 'web/static/tests/tours/**/*'),
            ('remove', 'web/static/tests/legacy/**/*'), # to remove when all legacy tests are ported
        ],
        'web.tests_assets': [
            ('include', 'web.assets_backend'),
            ('include', 'web.assets_backend_lazy'),

            'web/static/src/public/public_component_service.js',
            'web/static/tests/legacy/patch_translations.js',
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/legacy_tests/helpers/**/*',
            ('remove', 'web/static/tests/legacy/legacy_tests/helpers/test_utils_tests.js'),

            'web/static/lib/jquery/jquery.js',

            'web/static/lib/fullcalendar/core/index.global.js',
            'web/static/lib/fullcalendar/interaction/index.global.js',
            'web/static/lib/fullcalendar/daygrid/index.global.js',
            'web/static/lib/fullcalendar/timegrid/index.global.js',
            'web/static/lib/fullcalendar/list/index.global.js',
            'web/static/lib/fullcalendar/luxon3/index.global.js',

            'web/static/lib/zxing-library/zxing-library.js',

            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-javascript.js',
            'web/static/lib/ace/mode-qweb.js',
            'web/static/lib/ace/theme-monokai.js',
            'web/static/lib/stacktracejs/stacktrace.js',
            ('include', "web.chartjs_lib"),
            'web/static/lib/signature_pad/signature_pad.umd.js',

            'web/static/tests/legacy/helpers/**/*.js',
            'web/static/tests/legacy/views/helpers.js',
            'web/static/tests/legacy/search/helpers.js',
            'web/static/tests/legacy/views/calendar/helpers.js',
            'web/static/tests/legacy/webclient/**/helpers.js',
            'web/static/tests/legacy/qunit.js',
            'web/static/tests/legacy/main.js',
            'web/static/tests/legacy/mock_server_tests.js',
            'web/static/tests/legacy/setup.js',
            'web/static/tests/legacy/utils.js',
            'web/static/src/webclient/clickbot/clickbot.js',
        ],
        'web.qunit_suite_tests': [
            'web/static/tests/legacy/core/**/*.js',
            'web/static/tests/legacy/search/**/*.js',
            ('remove', 'web/static/tests/legacy/search/helpers.js'),
            'web/static/tests/legacy/views/**/*.js',
            ('remove', 'web/static/tests/legacy/views/helpers.js'),
            ('remove', 'web/static/tests/legacy/views/calendar/helpers.js'),
            'web/static/tests/legacy/webclient/**/*.js',
            ('remove', 'web/static/tests/legacy/webclient/**/helpers.js'),
            'web/static/tests/legacy/public/**/*.js',

            # Legacy
            'web/static/tests/legacy/legacy_tests/**/*.js',
            ('remove', 'web/static/tests/legacy/legacy_tests/helpers/**/*.js'),
        ],
        'web.qunit_mobile_suite_tests': [
            'web/static/tests/legacy/mobile/**/*.js',
        ],
        'web.assets_clickbot': [
            'web/static/src/webclient/clickbot/clickbot.js',
        ],
        "web.chartjs_lib" : [
            '/web/static/lib/Chart/Chart.js',
            '/web/static/lib/chartjs-adapter-luxon/chartjs-adapter-luxon.js',
        ],
        "web.fullcalendar_lib" : [
            '/web/static/lib/fullcalendar/core/index.global.js',
            '/web/static/lib/fullcalendar/core/locales-all.global.js',
            '/web/static/lib/fullcalendar/interaction/index.global.js',
            '/web/static/lib/fullcalendar/daygrid/index.global.js',
            '/web/static/lib/fullcalendar/luxon3/index.global.js',
            '/web/static/lib/fullcalendar/timegrid/index.global.js',
            '/web/static/lib/fullcalendar/list/index.global.js',
        ],
    },
    'bootstrap': True,  # load translations for login screen,
    'license': 'LGPL-3',
}
