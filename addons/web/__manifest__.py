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
        # Exemples:
        #   > web.assets_common = assets common to both frontend and backend clients.
        #   > web_editor.assets_wysiwyg = assets needed by components defined in the "web_editor" module.

        'web.assets_qweb': [
            'web/static/src/components/dialog/dialog.xml',

            'web/static/src/actions/**/*.xml',
            'web/static/src/commands/**/*.xml',
            'web/static/src/components/**/*.xml',
            'web/static/src/debug/**/*.xml',
            'web/static/src/effects/**/*.xml',
            'web/static/src/errors/**/*.xml',
            'web/static/src/notifications/**/*.xml',
            'web/static/src/webclient/**/*.xml',
            'web/static/src/webclient/switch_company_menu/switch_company_menu.xml',

            'web/static/src/legacy/xml/base.xml',
            'web/static/src/legacy/xml/chart.xml',
            'web/static/src/legacy/xml/fields.xml',
            'web/static/src/legacy/xml/file_upload_progress_bar.xml',
            'web/static/src/legacy/xml/file_upload_progress_card.xml',
            'web/static/src/legacy/xml/kanban.xml',
            'web/static/src/legacy/xml/notification.xml',
            'web/static/src/legacy/xml/pivot.xml',
            'web/static/src/legacy/xml/report.xml',
            'web/static/src/legacy/xml/search_panel.xml',
            'web/static/src/legacy/xml/web_calendar.xml',
            'web/static/src/legacy/xml/graph.xml',
            'web/static/src/legacy/xml/week_days.xml',
        ],
        'web.assets_common_minimal': [
            'web/static/lib/es6-promise/es6-promise-polyfill.js',
            'web/static/src/legacy/js/promise_extension.js',
            'web/static/src/boot.js',
        ],
        'web.assets_common': [
            ('include', 'web._assets_helpers'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_common_styles'),
            ('include', 'web.assets_common_minimal'),
            ('include', 'web._assets_common_scripts'),
        ],
        'web.assets_common_lazy': [
            ('include', 'web.assets_common'),
            # Remove assets_common_minimal
            ('remove', 'web/static/lib/es6-promise/es6-promise-polyfill.js'),
            ('remove', 'web/static/src/legacy/js/promise_extension.js'),
            ('remove', 'web/static/src/boot.js'),
        ],
        'web.assets_backend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap'),

            'base/static/src/css/modules.css',

            'web/static/src/legacy/scss/webclient_extra.scss',
            'web/static/src/legacy/scss/webclient_layout.scss',

            'web/static/src/legacy/scss/webclient.scss',
            'web/static/src/legacy/scss/domain_selector.scss',
            'web/static/src/legacy/scss/model_field_selector.scss',
            'web/static/src/legacy/scss/progress_bar.scss',
            'web/static/src/legacy/scss/dropdown.scss',
            'web/static/src/legacy/scss/tooltip.scss',
            'web/static/src/legacy/scss/switch_company_menu.scss',
            'web/static/src/legacy/scss/debug_manager.scss',
            'web/static/src/legacy/scss/control_panel.scss',
            'web/static/src/legacy/scss/fields.scss',
            'web/static/src/legacy/scss/file_upload.scss',
            'web/static/src/legacy/scss/views.scss',
            'web/static/src/legacy/scss/pivot_view.scss',
            'web/static/src/legacy/scss/graph_view.scss',
            'web/static/src/legacy/scss/form_view.scss',
            'web/static/src/legacy/scss/list_view.scss',
            'web/static/src/legacy/scss/kanban_dashboard.scss',
            'web/static/src/legacy/scss/kanban_examples_dialog.scss',
            'web/static/src/legacy/scss/kanban_column_progressbar.scss',
            'web/static/src/legacy/scss/kanban_view.scss',
            'web/static/src/legacy/scss/web_calendar.scss',
            'web/static/src/legacy/scss/search_view.scss',
            'web/static/src/legacy/scss/search_panel.scss',
            'web/static/src/legacy/scss/dropdown_menu.scss',
            'web/static/src/legacy/scss/data_export.scss',
            'base/static/src/scss/onboarding.scss',
            'web/static/src/legacy/scss/attachment_preview.scss',
            'web/static/src/legacy/scss/notification.scss',
            'web/static/src/legacy/scss/base_document_layout.scss',
            'web/static/src/legacy/scss/special_fields.scss',
            'web/static/src/legacy/scss/ribbon.scss',
            'web/static/src/legacy/scss/base_settings.scss',
            'web/static/src/legacy/scss/report_backend.scss',
            'web/static/src/legacy/scss/dropdown_extra.scss',
            'web/static/src/legacy/scss/fields_extra.scss',
            'web/static/src/legacy/scss/form_view_extra.scss',
            'web/static/src/legacy/scss/list_view_extra.scss',
            'web/static/src/legacy/scss/search_view_extra.scss',

            'web/static/src/utils/**/*.scss',
            'web/static/src/components/**/*.scss',
            'web/static/src/actions/**/*.scss',
            'web/static/src/hotkey/**/*.scss',
            'web/static/src/commands/**/*.scss',
            'web/static/src/notifications/**/*.scss',
            'web/static/src/effects/**/*.scss',
            'web/static/src/webclient/**/*.scss',

            'base/static/src/js/res_config_settings.js',
            'web/static/lib/jquery.scrollTo/jquery.scrollTo.js',
            'web/static/lib/fuzzy-master/fuzzy.js',
            'web/static/lib/Chart/Chart.js',  # TODO: lazy load it
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/py.js/lib/py.js',
            'web/static/lib/py.js/lib/py_extras.js',
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',

            'web/static/src/actions/**/*',
            'web/static/src/commands/**/*',
            'web/static/src/components/**/*',
            'web/static/src/core/**/*',
            'web/static/src/debug/**/*',
            'web/static/src/download/**/*',
            'web/static/src/effects/**/*',
            'web/static/src/errors/**/*',
            'web/static/src/hotkey/**/*',
            'web/static/src/localization/**/*',
            'web/static/src/notifications/**/*',
            'web/static/src/py_js/**/*',
            'web/static/src/services/**/*',
            'web/static/src/tools/test_menus_loader.js',
            'web/static/src/utils/**/*',
            'web/static/src/views/**/*',
            'web/static/src/webclient/**/*',
            'web/static/src/env.js',

            'web/static/src/legacy/action_adapters.js',
            'web/static/src/legacy/debug_manager.js',
            'web/static/src/legacy/service_provider_adapter.js',
            'web/static/src/legacy/legacy_client_actions.js',
            'web/static/src/legacy/legacy_dialog.js',
            'web/static/src/legacy/legacy_setup.js',
            'web/static/src/legacy/legacy_views.js',
            'web/static/src/legacy/root_widget.js',
            'web/static/src/legacy/systray_menu.js',
            'web/static/src/legacy/systray_menu_item.js',
            'web/static/src/legacy/utils.js',
            'web/static/src/legacy/web_client.js',
            'web/static/src/legacy/js/_deprecated/*',
            'web/static/src/legacy/js/chrome/*',
            'web/static/src/legacy/js/components/*',
            'web/static/src/legacy/js/control_panel/*',
            'web/static/src/legacy/js/core/domain.js',
            'web/static/src/legacy/js/core/mvc.js',
            'web/static/src/legacy/js/core/py_utils.js',
            'web/static/src/legacy/js/core/context.js',
            'web/static/src/legacy/js/core/data_comparison_utils.js',
            'web/static/src/legacy/js/core/math_utils.js',
            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/fields/*',
            'web/static/src/legacy/js/report/utils.js',
            'web/static/src/legacy/js/report/client_action.js',
            'web/static/src/legacy/js/services/data_manager.js',
            'web/static/src/legacy/js/services/report_service.js',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/tools/tools.js',
            'web/static/src/legacy/js/views/**/*',
            'web/static/src/legacy/js/widgets/change_password.js',
            'web/static/src/legacy/js/widgets/data_export.js',
            'web/static/src/legacy/js/widgets/date_picker.js',
            'web/static/src/legacy/js/widgets/domain_selector_dialog.js',
            'web/static/src/legacy/js/widgets/domain_selector.js',
            'web/static/src/legacy/js/widgets/iframe_widget.js',
            'web/static/src/legacy/js/widgets/model_field_selector.js',
            'web/static/src/legacy/js/widgets/pie_chart.js',
            'web/static/src/legacy/js/widgets/ribbon.js',
            'web/static/src/legacy/js/widgets/week_days.js',
            'web/static/src/legacy/js/widgets/signature.js',
            'web/static/src/legacy/js/widgets/attach_document.js',
            'web/static/src/legacy/js/apps.js',
            'web/static/src/legacy/js/env.js',
            'web/static/src/legacy/js/model.js',
            'web/static/src/legacy/js/owl_compatibility.js',
        ],
        'web.assets_frontend_minimal': [
            'web/static/src/legacy/js/public/lazyloader.js',
        ],
        'web.assets_frontend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_frontend_helpers'),

            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap'),

            'web/static/src/legacy/scss/base_frontend.scss',
            'web/static/src/legacy/scss/lazyloader.scss',
            'web/static/src/legacy/scss/navbar_mobile.scss',
            'web/static/src/legacy/scss/notification.scss',

            ('include', 'web.assets_frontend_minimal'),

            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/public/public_env.js',
            'web/static/src/legacy/js/public/public_crash_manager.js',
            'web/static/src/legacy/js/public/public_notification.js',
            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/public_root_instance.js',
            'web/static/src/legacy/js/public/public_widget.js',

            ('include', 'web.website_legacy'),
        ],
        'web.assets_frontend_lazy': [
            ('include', 'web.assets_frontend'),
            # Remove assets_frontend_minimal
            ('remove', 'web/static/src/legacy/js/public/lazyloader.js')
        ],
        'web.assets_backend_prod_only': [
            'web/static/src/main.js',
        ],
        # Optional Bundle for PDFJS lib
        # Since PDFJS is quite huge (80000≈ lines), please only load it when it is necessary.
        # For now, it is only use to display the PDF slide Viewer during an embed.
        # Bundlized, the size is reduced to 5300≈ lines.
        'web.pdf_js_lib': [
            'web/static/lib/pdfjs/build/pdf.js',
            'web/static/lib/pdfjs/build/pdf.worker.js',
        ],
        'web.report_assets_common': [
            ('include', 'web._assets_helpers'),

            'web/static/src/legacy/scss/bootstrap_overridden_report.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap'),

            'base/static/src/css/description.css',
            'web/static/lib/fontawesome/css/font-awesome.css',
            'web/static/src/legacy/scss/fonts.scss',
            'web/static/src/legacy/scss/report.scss',
            'web/static/src/legacy/scss/layout_standard.scss',
            'web/static/src/legacy/scss/layout_background.scss',
            'web/static/src/legacy/scss/layout_boxed.scss',
            'web/static/src/legacy/scss/layout_clean.scss',
            '/web/static/src/legacy/scss/asset_styles_company_report.scss',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/public_root_instance.js',
            'web/static/src/legacy/js/public/public_widget.js',
            'web/static/src/legacy/js/report/utils.js',
            'web/static/src/legacy/js/report/report.js',
        ],
        'web.report_assets_pdf': [
            'web/static/src/css/reset.min.css',
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
        #
        # Exemples:
        #   > web._assets_helpers = define assets needed in most main bundles

        'web._assets_primary_variables': [
            'web/static/src/legacy/scss/primary_variables.scss',
        ],
        'web._assets_secondary_variables': [
            'web/static/src/legacy/scss/secondary_variables.scss',
        ],
        'web._assets_helpers': [
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_mixins.scss',
            'web/static/src/legacy/scss/bs_mixins_overrides.scss',
            'web/static/src/legacy/scss/utils.scss',

            ('include', 'web._assets_primary_variables'),
            ('include', 'web._assets_secondary_variables'),
        ],
        'web._assets_bootstrap': [
            'web/static/src/legacy/scss/import_bootstrap.scss',
            'web/static/src/legacy/scss/bootstrap_review.scss',
        ],
        'web._assets_backend_helpers': [
            'web/static/src/legacy/scss/bootstrap_overridden.scss',
        ],
        'web._assets_frontend_helpers': [
            'web/static/src/legacy/scss/bootstrap_overridden_frontend.scss',
        ],
        'web._assets_common_styles': [
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/lib/fontawesome/css/font-awesome.css',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/lib/tempusdominus/tempusdominus.scss',
            'web/static/src/legacy/scss/fonts.scss',
            'web/static/src/legacy/scss/ui.scss',
            'web/static/src/legacy/scss/ui_extra.scss',
            'web/static/src/legacy/scss/navbar.scss',
            'web/static/src/legacy/scss/mimetypes.scss',
            'web/static/src/legacy/scss/modal.scss',
            'web/static/src/legacy/scss/animation.scss',
            'web/static/src/legacy/scss/datepicker.scss',
            'web/static/src/legacy/scss/daterangepicker.scss',
            'web/static/src/legacy/scss/banner.scss',
            'web/static/src/legacy/scss/colorpicker.scss',
            'web/static/src/legacy/scss/popover.scss',
            'web/static/src/legacy/scss/translation_dialog.scss',
            'web/static/src/legacy/scss/keyboard.scss',
            'web/static/src/legacy/scss/name_and_signature.scss',
            'web/static/src/legacy/scss/web.zoomodoo.scss',
            'web/static/src/legacy/scss/color_picker.scss',
            'web/static/src/legacy/scss/fontawesome_overridden.scss',
        ],
        'web._assets_common_scripts': [
            'web/static/lib/underscore/underscore.js',
            'web/static/lib/underscore.string/lib/underscore.string.js',
            'web/static/lib/moment/moment.js',
            'web/static/lib/owl/owl.js',
            'web/static/src/legacy/js/component_extension.js',
            'web/static/lib/jquery/jquery.js',
            'web/static/lib/jquery.ui/jquery-ui.js',
            'web/static/lib/jquery/jquery.browser.js',
            'web/static/lib/jquery.blockUI/jquery.blockUI.js',
            'web/static/lib/jquery.hotkeys/jquery.hotkeys.js',
            'web/static/lib/jquery.placeholder/jquery.placeholder.js',
            'web/static/lib/jquery.form/jquery.form.js',
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',
            'web/static/lib/jquery.mjs.nestedSortable/jquery.mjs.nestedSortable.js',
            'web/static/lib/popper/popper.js',
            'web/static/lib/bootstrap/js/index.js',
            'web/static/lib/bootstrap/js/util.js',
            'web/static/lib/bootstrap/js/alert.js',
            'web/static/lib/bootstrap/js/button.js',
            'web/static/lib/bootstrap/js/carousel.js',
            'web/static/lib/bootstrap/js/collapse.js',
            'web/static/lib/bootstrap/js/dropdown.js',
            'web/static/lib/bootstrap/js/modal.js',
            'web/static/lib/bootstrap/js/tooltip.js',
            'web/static/lib/bootstrap/js/popover.js',
            'web/static/lib/bootstrap/js/scrollspy.js',
            'web/static/lib/bootstrap/js/tab.js',
            'web/static/lib/bootstrap/js/toast.js',
            'web/static/lib/tempusdominus/tempusdominus.js',
            'web/static/lib/select2/select2.js',
            'web/static/lib/clipboard/clipboard.js',
            'web/static/lib/jSignature/jSignatureCustom.js',
            'web/static/lib/qweb/qweb2.js',
            'web/static/src/legacy/js/libs/autocomplete.js',
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/content-disposition.js',
            'web/static/src/legacy/js/libs/download.js',
            'web/static/src/legacy/js/libs/fullcalendar.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web/static/src/legacy/js/libs/underscore.js',
            'web/static/src/legacy/js/libs/popper.js',
            'web/static/src/legacy/js/libs/zoomodoo.js',
            'web/static/src/legacy/js/core/keyboard_navigation_mixin.js',
            'web/static/src/legacy/js/core/abstract_service.js',
            'web/static/src/legacy/js/core/abstract_storage_service.js',
            'web/static/src/legacy/js/core/ajax.js',
            'web/static/src/legacy/js/core/browser_detection.js',
            'web/static/src/legacy/js/core/bus.js',
            'web/static/src/legacy/js/core/custom_hooks.js',
            'web/static/src/legacy/js/core/class.js',
            'web/static/src/legacy/js/core/collections.js',
            'web/static/src/legacy/js/core/concurrency.js',
            'web/static/src/legacy/js/core/dialog.js',
            'web/static/src/legacy/js/core/owl_dialog.js',
            'web/static/src/legacy/js/core/popover.js',
            'web/static/src/legacy/js/core/dom.js',
            'web/static/src/legacy/js/core/local_storage.js',
            'web/static/src/legacy/js/core/mixins.js',
            'web/static/src/legacy/js/core/qweb.js',
            'web/static/src/legacy/js/core/ram_storage.js',
            'web/static/src/legacy/js/core/registry.js',
            'web/static/src/legacy/js/core/rpc.js',
            'web/static/src/legacy/js/core/service_mixins.js',
            'web/static/src/legacy/js/core/session.js',
            'web/static/src/legacy/js/core/session_storage.js',
            'web/static/src/legacy/js/core/time.js',
            'web/static/src/legacy/js/core/translation.js',
            'web/static/src/legacy/js/core/utils.js',
            'web/static/src/legacy/js/core/widget.js',
            'web/static/src/legacy/js/services/ajax_service.js',
            'web/static/src/legacy/js/services/config.js',
            'web/static/src/legacy/js/services/core.js',
            'web/static/src/legacy/js/services/local_storage_service.js',
            'web/static/src/legacy/js/services/notification_service.js',
            'web/static/src/legacy/js/services/crash_manager.js',
            'web/static/src/legacy/js/core/error_utils.js',
            'web/static/src/legacy/js/services/session_storage_service.js',
            'web/static/src/legacy/js/tools/debug_manager.js',
            'web/static/src/legacy/js/common_env.js',
            'web/static/src/legacy/js/widgets/name_and_signature.js',
            'web/static/src/legacy/js/widgets/notification.js',
            'web/static/src/legacy/js/core/smooth_scroll_on_drag.js',
            'web/static/src/legacy/js/widgets/colorpicker.js',
            'web/static/src/legacy/js/widgets/translation_dialog.js',
        ],

        # Used during the transition of the web architecture
        'web.website_legacy': [
            # Old rainbow man kept for website compatibility
            'web/static/src/legacy/frontend/rainbowman/*.js',
            'web/static/src/legacy/frontend/rainbowman/*.scss',
        ],

        # ---------------------------------------------------------------------
        # TESTS BUNDLES
        # ---------------------------------------------------------------------

        'web.assets_tests': [
            # No tours are defined in web, but the bundle "assets_tests" is
            # first called in web.
            'web/static/tests/legacy/helpers/test_utils_file.js'
        ],
        'web.tests_assets': [
            'web/static/lib/daterangepicker/daterangepicker.css',
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/helpers/**/*',

            'web/static/lib/fullcalendar/core/main.css',
            'web/static/lib/fullcalendar/daygrid/main.css',
            'web/static/lib/fullcalendar/timegrid/main.css',
            'web/static/lib/fullcalendar/list/main.css',
            'web/static/lib/fullcalendar/core/main.js',
            'web/static/lib/fullcalendar/moment/main.js',
            'web/static/lib/fullcalendar/interaction/main.js',
            'web/static/lib/fullcalendar/daygrid/main.js',
            'web/static/lib/fullcalendar/timegrid/main.js',
            'web/static/lib/fullcalendar/list/main.js',
            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/javascript_highlight_rules.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-js.js',
            'web/static/lib/Chart/Chart.js',
            'web/static/lib/nearest/jquery.nearest.js',
            'web/static/lib/daterangepicker/daterangepicker.js',
            'web/static/lib/stacktracejs/stacktrace.js',

            # 'web/static/tests/legacy/main_tests.js',
            'web/static/tests/helpers/**/*.js',
            'web/static/tests/qunit.js',
            'web/static/tests/main.js',
            'web/static/tests/setup.js',
        ],
        'web.qunit_suite_tests': [
            'base/static/tests/base_settings_tests.js',
            'web/static/tests/legacy/components/action_menus_tests.js',
            'web/static/tests/legacy/components/custom_checkbox_tests.js',
            'web/static/tests/legacy/components/custom_file_input_tests.js',
            'web/static/tests/legacy/components/datepicker_tests.js',
            'web/static/tests/legacy/components/dropdown_menu_tests.js',
            'web/static/tests/legacy/components/pager_tests.js',
            'web/static/tests/legacy/control_panel/**/*.js',
            'web/static/tests/legacy/core/**/*.js',
            'web/static/tests/legacy/fields/relational_fields/**/*.js',
            'web/static/tests/legacy/fields/basic_fields_tests.js',
            'web/static/tests/legacy/fields/field_utils_tests.js',
            'web/static/tests/legacy/fields/relational_fields_tests.js',
            'web/static/tests/legacy/fields/signature_tests.js',
            'web/static/tests/legacy/fields/special_fields_tests.js',
            'web/static/tests/legacy/fields/upgrade_fields_tests.js',
            'web/static/tests/legacy/services/**/*.js',
            'web/static/tests/legacy/tools/**/*.js',
            'web/static/tests/legacy/views/abstract_controller_tests.js',
            'web/static/tests/legacy/views/abstract_model_tests.js',
            'web/static/tests/legacy/views/abstract_view_banner_tests.js',
            'web/static/tests/legacy/views/abstract_view_tests.js',
            'web/static/tests/legacy/views/basic_model_tests.js',
            'web/static/tests/legacy/views/calendar_tests.js',
            'web/static/tests/legacy/views/form_tests.js',
            'web/static/tests/legacy/views/graph_tests.js',
            'web/static/tests/legacy/views/kanban_model_tests.js',
            'web/static/tests/legacy/views/kanban_tests.js',
            'web/static/tests/legacy/views/list_tests.js',
            'web/static/tests/legacy/views/pivot_tests.js',
            'web/static/tests/legacy/views/qweb_tests.js',
            'web/static/tests/legacy/views/sample_server_tests.js',
            'web/static/tests/legacy/views/search_panel_tests.js',
            'web/static/tests/legacy/views/view_dialogs_tests.js',
            'web/static/tests/legacy/widgets/**/*.js',
            'web/static/tests/legacy/report/**/*.js',
            'web/static/tests/legacy/component_extension_tests.js',
            'web/static/tests/legacy/mockserver_tests.js',
            'web/static/tests/legacy/owl_compatibility_tests.js',
            'web/static/tests/legacy/qweb_tests.js',

            'web/static/tests/actions/**/*.js',
            'web/static/tests/components/**/*.js',
            'web/static/tests/core/**/*.js',
            'web/static/tests/debug/**/*.js',
            'web/static/tests/effects/**/*.js',
            'web/static/tests/errors/**/*.js',
            'web/static/tests/localization/**/*.js',
            'web/static/tests/notifications/**/*.js',
            'web/static/tests/py_js/**/*.js',
            'web/static/tests/services/**/*.js',
            'web/static/tests/utils/**/*.js',
            'web/static/tests/webclient/**/*.js',
        ],
        'web.qunit_mobile_suite_tests': [
            'web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js',
            # 'web/static/tests/legacy/fields/basic_fields_mobile_tests.js',
            # 'web/static/tests/legacy/fields/relational_fields_mobile_tests.js',
            # 'web/static/tests/legacy/components/dropdown_menu_mobile_tests.js',
        ],
    },
    'bootstrap': True,  # load translations for login screen
}
