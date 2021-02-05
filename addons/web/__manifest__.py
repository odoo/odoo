# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web',
    'category': 'Hidden',
    'version': '1.0',
    'description':
        """
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
    'bootstrap': True,  # load translations for login screen
    'assets': {
        'report_assets_common': [
            # new module 
            'web/static/src/scss/bootstrap_overridden_report.scss',
            # None None
            ('include', 'web._assets_bootstrap'),
            # new module 
            'base/static/src/css/description.css',
            # new module 
            'web/static/lib/fontawesome/css/font-awesome.css',
            # new module 
            'web/static/src/scss/fonts.scss',
            # new module 
            'web/static/src/scss/report.scss',
            # new module 
            'web/static/src/scss/layout_standard.scss',
            # new module 
            'web/static/src/scss/layout_background.scss',
            # new module 
            'web/static/src/scss/layout_boxed.scss',
            # new module 
            'web/static/src/scss/layout_clean.scss',
            # new module 
            'web/static/src/scss/asset_styles_company_report.scss',
            # new module 
            'web/static/src/js/services/session.js',
            # new module 
            'web/static/src/js/public/public_root.js',
            # new module 
            'web/static/src/js/public/public_root_instance.js',
            # new module 
            'web/static/src/js/public/public_widget.js',
            # new module 
            'web/static/src/js/report/utils.js',
            # new module 
            'web/static/src/js/report/report.js',
        ],
        'report_assets_pdf': [
            # new module 
            'web/static/src/css/reset.min.css',
        ],
        '_assets_utils': [
            # new module 
            'web/static/lib/bootstrap/scss/_functions.scss',
            # new module 
            'web/static/lib/bootstrap/scss/_mixins.scss',
            # new module 
            'web/static/src/scss/bs_mixins_overrides.scss',
            # new module 
            'web/static/src/scss/utils.scss',
        ],
        '_assets_primary_variables': [
            # new module 
            'web/static/src/scss/primary_variables.scss',
        ],
        '_assets_secondary_variables': [
            # new module 
            'web/static/src/scss/secondary_variables.scss',
        ],
        '_assets_helpers': [
            # None None
            ('include', 'web._assets_utils'),
            # None None
            ('include', 'web._assets_primary_variables'),
            # None None
            ('include', 'web._assets_secondary_variables'),
            # None None
            # raw need to be manually included
            # new module 
            'web/static/lib/bootstrap/scss/_variables.scss',
        ],
        '_assets_backend_helpers': [
            # new module 
            'web/static/src/scss/bootstrap_overridden.scss',
        ],
        '_assets_frontend_helpers': [
            # new module 
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
        ],
        '_assets_bootstrap': [
            # new module 
            'web/static/src/scss/import_bootstrap.scss',
            # new module 
            'web/static/src/scss/bootstrap_review.scss',
        ],
        '_assets_common_minimal_js': [
            # new module 
            'web/static/lib/es6-promise/es6-promise-polyfill.js',
            # new module 
            'web/static/src/js/promise_extension.js',
            # new module 
            'web/static/src/js/boot.js',
        ],
        'assets_common_minimal_js': [
            # None None
            ('include', 'web._assets_common_minimal_js'),
        ],
        'assets_common': [
            # None None
            ('include', 'web._assets_helpers'),
            # new module 
            'web/static/lib/jquery.ui/jquery-ui.css',
            # new module 
            'web/static/lib/fontawesome/css/font-awesome.css',
            # new module 
            'web/static/lib/select2/select2.css',
            # new module 
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            # new module 
            'web/static/lib/tempusdominus/tempusdominus.scss',
            # new module 
            'web/static/src/scss/fonts.scss',
            # new module 
            'web/static/src/scss/ui.scss',
            # new module 
            'web/static/src/scss/ui_extra.scss',
            # new module 
            'web/static/src/scss/navbar.scss',
            # new module 
            'web/static/src/scss/mimetypes.scss',
            # new module 
            'web/static/src/scss/modal.scss',
            # new module 
            'web/static/src/scss/animation.scss',
            # new module 
            'web/static/src/scss/rainbow.scss',
            # new module 
            'web/static/src/scss/datepicker.scss',
            # new module 
            'web/static/src/scss/daterangepicker.scss',
            # new module 
            'web/static/src/scss/banner.scss',
            # new module 
            'web/static/src/scss/colorpicker.scss',
            # new module 
            'web/static/src/scss/popover.scss',
            # new module 
            'web/static/src/scss/translation_dialog.scss',
            # new module 
            'web/static/src/scss/keyboard.scss',
            # new module 
            'web/static/src/scss/name_and_signature.scss',
            # new module 
            'web/static/src/scss/web.zoomodoo.scss',
            # new module 
            'web/static/src/scss/color_picker.scss',
            # new module 
            'web/static/src/scss/fontawesome_overridden.scss',
            # None None
            ('include', 'web._assets_common_minimal_js'),
            # new module 
            'web/static/lib/underscore/underscore.js',
            # new module 
            'web/static/lib/underscore.string/lib/underscore.string.js',
            # new module 
            'web/static/lib/moment/moment.js',
            # new module 
            'web/static/lib/owl/owl.js',
            # new module 
            'web/static/src/js/component_extension.js',
            # new module 
            'web/static/lib/jquery/jquery.js',
            # new module 
            'web/static/lib/jquery.ui/jquery-ui.js',
            # new module 
            'web/static/lib/jquery/jquery.browser.js',
            # new module 
            'web/static/lib/jquery.blockUI/jquery.blockUI.js',
            # new module 
            'web/static/lib/jquery.hotkeys/jquery.hotkeys.js',
            # new module 
            'web/static/lib/jquery.placeholder/jquery.placeholder.js',
            # new module 
            'web/static/lib/jquery.form/jquery.form.js',
            # new module 
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',
            # new module 
            'web/static/lib/jquery.mjs.nestedSortable/jquery.mjs.nestedSortable.js',
            # new module 
            'web/static/lib/popper/popper.js',
            # new module 
            'web/static/lib/bootstrap/js/index.js',
            # new module 
            'web/static/lib/bootstrap/js/util.js',
            # new module 
            'web/static/lib/bootstrap/js/alert.js',
            # new module 
            'web/static/lib/bootstrap/js/button.js',
            # new module 
            'web/static/lib/bootstrap/js/carousel.js',
            # new module 
            'web/static/lib/bootstrap/js/collapse.js',
            # new module 
            'web/static/lib/bootstrap/js/dropdown.js',
            # new module 
            'web/static/lib/bootstrap/js/modal.js',
            # new module 
            'web/static/lib/bootstrap/js/tooltip.js',
            # new module 
            'web/static/lib/bootstrap/js/popover.js',
            # new module 
            'web/static/lib/bootstrap/js/scrollspy.js',
            # new module 
            'web/static/lib/bootstrap/js/tab.js',
            # new module 
            'web/static/lib/bootstrap/js/toast.js',
            # new module 
            'web/static/lib/tempusdominus/tempusdominus.js',
            # new module 
            'web/static/lib/select2/select2.js',
            # new module 
            'web/static/lib/clipboard/clipboard.js',
            # new module 
            'web/static/lib/jSignature/jSignatureCustom.js',
            # new module 
            'web/static/lib/qweb/qweb2.js',
            # new module 
            'web/static/src/js/libs/autocomplete.js',
            # new module 
            'web/static/src/js/libs/bootstrap.js',
            # new module 
            'web/static/src/js/libs/jquery.js',
            # new module 
            'web/static/src/js/libs/download.js',
            # new module 
            'web/static/src/js/libs/content-disposition.js',
            # new module 
            'web/static/src/js/libs/underscore.js',
            # new module 
            'web/static/src/js/libs/fullcalendar.js',
            # new module 
            'web/static/src/js/chrome/keyboard_navigation_mixin.js',
            # new module 
            'web/static/src/js/core/abstract_service.js',
            # new module 
            'web/static/src/js/core/abstract_storage_service.js',
            # new module 
            'web/static/src/js/core/ajax.js',
            # new module 
            'web/static/src/js/core/browser_detection.js',
            # new module 
            'web/static/src/js/core/bus.js',
            # new module 
            'web/static/src/js/core/custom_hooks.js',
            # new module 
            'web/static/src/js/core/class.js',
            # new module 
            'web/static/src/js/core/collections.js',
            # new module 
            'web/static/src/js/core/concurrency.js',
            # new module 
            'web/static/src/js/core/dialog.js',
            # new module 
            'web/static/src/js/core/owl_dialog.js',
            # new module 
            'web/static/src/js/core/popover.js',
            # new module 
            'web/static/src/js/core/dom.js',
            # new module 
            'web/static/src/js/core/local_storage.js',
            # new module 
            'web/static/src/js/core/mixins.js',
            # new module 
            'web/static/src/js/core/patch_mixin.js',
            # new module 
            'web/static/src/js/core/qweb.js',
            # new module 
            'web/static/src/js/core/ram_storage.js',
            # new module 
            'web/static/src/js/core/registry.js',
            # new module 
            'web/static/src/js/core/rpc.js',
            # new module 
            'web/static/src/js/core/service_mixins.js',
            # new module 
            'web/static/src/js/core/session.js',
            # new module 
            'web/static/src/js/core/session_storage.js',
            # new module 
            'web/static/src/js/core/time.js',
            # new module 
            'web/static/src/js/core/translation.js',
            # new module 
            'web/static/src/js/core/utils.js',
            # new module 
            'web/static/src/js/core/widget.js',
            # new module 
            'web/static/src/js/services/ajax_service.js',
            # new module 
            'web/static/src/js/services/config.js',
            # new module 
            'web/static/src/js/services/core.js',
            # new module 
            'web/static/src/js/services/local_storage_service.js',
            # new module 
            'web/static/src/js/services/notification_service.js',
            # new module 
            'web/static/src/js/services/crash_manager.js',
            # new module 
            'web/static/src/js/services/session_storage_service.js',
            # new module 
            'web/static/src/js/tools/debug_manager.js',
            # new module 
            'web/static/src/js/common_env.js',
            # new module 
            'web/static/src/js/widgets/name_and_signature.js',
            # new module 
            'web/static/src/js/widgets/notification.js',
            # new module 
            'web/static/src/js/widgets/rainbow_man.js',
            # new module 
            'web/static/src/js/core/smooth_scroll_on_drag.js',
            # new module 
            'web/static/src/js/widgets/colorpicker.js',
            # new module 
            'web/static/src/js/widgets/translation_dialog.js',
            # new module 
            'web/static/src/js/libs/zoomodoo.js',
        ],
        'web.assets_common': [
            # replace //t[@t-call='web._assets_common_minimal_js']
            ('replace', 'web._assets_common_minimal_js', 'web._assets_common_minimal_js'),
        ],
        'assets_backend': [
            # None None
            ('include', 'web._assets_backend_helpers'),
            # None None
            ('include', 'web._assets_bootstrap'),
            # new module 
            'base/static/src/css/modules.css',
            # new module 
            'web/static/src/scss/webclient_extra.scss',
            # new module 
            'web/static/src/scss/webclient_layout.scss',
            # new module 
            'web/static/src/scss/webclient.scss',
            # new module 
            'web/static/src/scss/domain_selector.scss',
            # new module 
            'web/static/src/scss/model_field_selector.scss',
            # new module 
            'web/static/src/scss/progress_bar.scss',
            # new module 
            'web/static/src/scss/dropdown.scss',
            # new module 
            'web/static/src/scss/dropdown_extra.scss',
            # new module 
            'web/static/src/scss/tooltip.scss',
            # new module 
            'web/static/src/scss/switch_company_menu.scss',
            # new module 
            'web/static/src/scss/debug_manager.scss',
            # new module 
            'web/static/src/scss/control_panel.scss',
            # new module 
            'web/static/src/scss/fields.scss',
            # new module 
            'web/static/src/scss/fields_extra.scss',
            # new module 
            'web/static/src/scss/file_upload.scss',
            # new module 
            'web/static/src/scss/views.scss',
            # new module 
            'web/static/src/scss/pivot_view.scss',
            # new module 
            'web/static/src/scss/graph_view.scss',
            # new module 
            'web/static/src/scss/form_view.scss',
            # new module 
            'web/static/src/scss/form_view_extra.scss',
            # new module 
            'web/static/src/scss/list_view.scss',
            # new module 
            'web/static/src/scss/list_view_extra.scss',
            # new module 
            'web/static/src/scss/kanban_dashboard.scss',
            # new module 
            'web/static/src/scss/kanban_examples_dialog.scss',
            # new module 
            'web/static/src/scss/kanban_column_progressbar.scss',
            # new module 
            'web/static/src/scss/kanban_view.scss',
            # new module 
            'web/static/src/scss/web_calendar.scss',
            # new module 
            'web/static/src/scss/search_view.scss',
            # new module 
            'web/static/src/scss/search_panel.scss',
            # new module 
            'web/static/src/scss/dropdown_menu.scss',
            # new module 
            'web/static/src/scss/search_view_extra.scss',
            # new module 
            'web/static/src/scss/data_export.scss',
            # new module 
            'base/static/src/scss/onboarding.scss',
            # new module 
            'web/static/src/scss/attachment_preview.scss',
            # new module 
            'web/static/src/scss/notification.scss',
            # new module 
            'web/static/src/scss/base_document_layout.scss',
            # new module 
            'web/static/src/scss/special_fields.scss',
            # new module 
            'web/static/src/scss/ribbon.scss',
            # new module 
            'web/static/src/scss/base_settings.scss',
            # new module 
            'base/static/src/js/res_config_settings.js',
            # new module 
            'web/static/lib/jquery.scrollTo/jquery.scrollTo.js',
            # new module 
            'web/static/lib/fuzzy-master/fuzzy.js',
            # new module 
            'web/static/lib/py.js/lib/py.js',
            # new module 
            'web/static/lib/py.js/lib/py_extras.js',
            # new module 
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',
            # new module 
            'web/static/src/js/core/domain.js',
            # new module 
            'web/static/src/js/core/mvc.js',
            # new module 
            'web/static/src/js/core/py_utils.js',
            # new module 
            'web/static/src/js/chrome/abstract_action.js',
            # new module 
            'web/static/src/js/chrome/action_manager.js',
            # new module 
            'web/static/src/js/chrome/action_manager_act_window.js',
            # new module 
            'web/static/src/js/chrome/action_manager_report.js',
            # new module 
            'web/static/src/js/chrome/action_mixin.js',
            # new module 
            'web/static/src/js/chrome/abstract_web_client.js',
            # new module 
            'web/static/src/js/chrome/web_client.js',
            # new module 
            'web/static/src/js/chrome/root_widget.js',
            # new module 
            'web/static/src/js/_deprecated/data.js',
            # new module 
            'web/static/src/js/core/context.js',
            # new module 
            'web/static/src/js/core/data_comparison_utils.js',
            # new module 
            'web/static/src/js/core/math_utils.js',
            # new module 
            'web/static/src/js/core/misc.js',
            # new module 
            'web/static/src/js/services/crash_manager_service.js',
            # new module 
            'web/static/src/js/services/data_manager.js',
            # new module 
            'web/static/src/js/services/report_service.js',
            # new module 
            'web/static/src/js/services/session.js',
            # new module 
            'web/static/src/js/widgets/change_password.js',
            # new module 
            'web/static/src/js/tools/test_menus_loader.js',
            # new module 
            'web/static/src/js/tools/debug_manager_backend.js',
            # new module 
            'web/static/src/js/tools/tools.js',
            # new module 
            'web/static/src/js/env.js',
            # new module 
            'web/static/src/js/widgets/data_export.js',
            # new module 
            'web/static/src/js/widgets/date_picker.js',
            # new module 
            'web/static/src/js/widgets/domain_selector_dialog.js',
            # new module 
            'web/static/src/js/widgets/domain_selector.js',
            # new module 
            'web/static/src/js/widgets/iframe_widget.js',
            # new module 
            'web/static/src/js/chrome/loading.js',
            # new module 
            'web/static/src/js/widgets/model_field_selector.js',
            # new module 
            'web/static/src/js/chrome/systray_menu.js',
            # new module 
            'web/static/src/js/widgets/switch_company_menu.js',
            # new module 
            'web/static/src/js/chrome/user_menu.js',
            # new module 
            'web/static/src/js/chrome/menu.js',
            # new module 
            'web/static/src/js/chrome/apps_menu.js',
            # new module 
            'web/static/src/js/widgets/pie_chart.js',
            # new module 
            'web/static/src/js/widgets/ribbon.js',
            # new module 
            'web/static/src/js/widgets/signature.js',
            # new module 
            'web/static/src/js/components/action_menus.js',
            # new module 
            'web/static/src/js/components/dropdown_menu.js',
            # new module 
            'web/static/src/js/components/dropdown_menu_item.js',
            # new module 
            'web/static/src/js/components/custom_checkbox.js',
            # new module 
            'web/static/src/js/components/custom_file_input.js',
            # new module 
            'web/static/src/js/components/datepicker.js',
            # new module 
            'web/static/src/js/components/pager.js',
            # new module 
            'web/static/src/js/apps.js',
            # new module 
            'web/static/src/js/_deprecated/basic_fields.js',
            # new module 
            'web/static/src/js/fields/abstract_field.js',
            # new module 
            'web/static/src/js/fields/basic_fields.js',
            # new module 
            'web/static/src/js/fields/field_registry.js',
            # new module 
            'web/static/src/js/fields/field_registry_owl.js',
            # new module 
            'web/static/src/js/views/basic/widget_registry.js',
            # new module 
            'web/static/src/js/fields/field_utils.js',
            # new module 
            'web/static/src/js/fields/relational_fields.js',
            # new module 
            'web/static/src/js/fields/special_fields.js',
            # new module 
            'web/static/src/js/fields/upgrade_fields.js',
            # new module 
            'web/static/src/js/fields/field_wrapper.js',
            # new module 
            'web/static/src/js/fields/abstract_field_owl.js',
            # new module 
            'web/static/src/js/fields/basic_fields_owl.js',
            # new module 
            'web/static/src/js/views/abstract_view.js',
            # new module 
            'web/static/src/js/views/abstract_renderer.js',
            # new module 
            'web/static/src/js/views/abstract_renderer_owl.js',
            # new module 
            'web/static/src/js/views/abstract_model.js',
            # new module 
            'web/static/src/js/model.js',
            # new module 
            'web/static/src/js/views/abstract_controller.js',
            # new module 
            'web/static/src/js/views/renderer_wrapper.js',
            # new module 
            'web/static/src/js/views/basic/basic_model.js',
            # new module 
            'web/static/src/js/views/basic/basic_view.js',
            # new module 
            'web/static/src/js/views/basic/basic_controller.js',
            # new module 
            'web/static/src/js/views/basic/basic_renderer.js',
            # new module 
            'web/static/src/js/control_panel/comparison_menu.js',
            # new module 
            'web/static/src/js/control_panel/control_panel.js',
            # new module 
            'web/static/src/js/control_panel/control_panel_model_extension.js',
            # new module 
            'web/static/src/js/control_panel/control_panel_x2many.js',
            # new module 
            'web/static/src/js/control_panel/custom_favorite_item.js',
            # new module 
            'web/static/src/js/control_panel/favorite_menu.js',
            # new module 
            'web/static/src/js/control_panel/custom_filter_item.js',
            # new module 
            'web/static/src/js/control_panel/filter_menu.js',
            # new module 
            'web/static/src/js/control_panel/groupby_menu.js',
            # new module 
            'web/static/src/js/control_panel/custom_group_by_item.js',
            # new module 
            'web/static/src/js/control_panel/search_bar.js',
            # new module 
            'web/static/src/js/control_panel/search_utils.js',
            # new module 
            'web/static/src/js/views/search_panel_model_extension.js',
            # new module 
            'web/static/src/js/views/search_panel.js',
            # new module 
            'web/static/src/js/views/action_model.js',
            # new module 
            'web/static/src/js/views/field_manager_mixin.js',
            # new module 
            'web/static/src/js/views/file_upload_mixin.js',
            # new module 
            'web/static/src/js/views/file_upload_progress_bar.js',
            # new module 
            'web/static/src/js/views/file_upload_progress_card.js',
            # new module 
            'web/static/src/js/views/sample_server.js',
            # new module 
            'web/static/src/js/views/select_create_controllers_registry.js',
            # new module 
            'web/static/src/js/views/signature_dialog.js',
            # new module 
            'web/static/src/js/views/standalone_field_manager_mixin.js',
            # new module 
            'web/static/src/js/views/view_registry.js',
            # new module 
            'web/static/src/js/views/view_dialogs.js',
            # new module 
            'web/static/src/js/views/view_utils.js',
            # new module 
            'web/static/src/js/views/form/form_renderer.js',
            # new module 
            'web/static/src/js/views/form/form_controller.js',
            # new module 
            'web/static/src/js/views/form/form_view.js',
            # new module 
            'web/static/src/js/views/graph/graph_model.js',
            # new module 
            'web/static/src/js/views/graph/graph_controller.js',
            # new module 
            'web/static/src/js/views/graph/graph_renderer.js',
            # new module 
            'web/static/src/js/views/graph/graph_view.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_column.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_column_progressbar.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_column_quick_create.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_model.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_controller.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_examples_registry.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_record.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_record_quick_create.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_renderer.js',
            # new module 
            'web/static/src/js/views/kanban/kanban_view.js',
            # new module 
            'web/static/src/js/views/kanban/quick_create_form_view.js',
            # new module 
            'web/static/src/js/views/list/list_editable_renderer.js',
            # new module 
            'web/static/src/js/views/list/list_model.js',
            # new module 
            'web/static/src/js/views/list/list_renderer.js',
            # new module 
            'web/static/src/js/views/list/list_view.js',
            # new module 
            'web/static/src/js/views/list/list_controller.js',
            # new module 
            'web/static/src/js/views/list/list_confirm_dialog.js',
            # new module 
            'web/static/src/js/views/pivot/pivot_model.js',
            # new module 
            'web/static/src/js/views/pivot/pivot_controller.js',
            # new module 
            'web/static/src/js/views/pivot/pivot_renderer.js',
            # new module 
            'web/static/src/js/views/pivot/pivot_view.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_controller.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_model.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_popover.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_quick_create.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_renderer.js',
            # new module 
            'web/static/src/js/views/calendar/calendar_view.js',
            # new module 
            'web/static/src/js/views/qweb/qweb_view.js',
            # new module 
            'web/static/src/js/widgets/attach_document.js',
            # new module 
            'web/static/src/js/fields/signature.js',
            # new module 
            'web/static/src/js/owl_compatibility.js',
            # new module 
            'web/static/src/js/report/utils.js',
            # new module 
            'web/static/src/js/report/client_action.js',
            # new module 
            'web/static/src/scss/report_backend.scss',
        ],
        '_assets_frontend_minimal_js': [
            # new module 
            'web/static/src/js/public/lazyloader.js',
        ],
        'assets_frontend_minimal_js': [
            # None None
            ('include', 'web._assets_frontend_minimal_js'),
        ],
        'assets_frontend': [
            # None None
            ('include', 'web._assets_frontend_helpers'),
            # None None
            ('include', 'web._assets_bootstrap'),
            # new module 
            'web/static/src/scss/base_frontend.scss',
            # new module 
            'web/static/src/scss/lazyloader.scss',
            # new module 
            'web/static/src/scss/navbar_mobile.scss',
            # new module 
            'web/static/src/scss/notification.scss',
            # None None
            ('include', 'web._assets_frontend_minimal_js'),
            # new module 
            'web/static/src/js/services/session.js',
            # new module 
            'web/static/src/js/public/public_env.js',
            # new module 
            'web/static/src/js/public/public_crash_manager.js',
            # new module 
            'web/static/src/js/public/public_notification.js',
            # new module 
            'web/static/src/js/public/public_root.js',
            # new module 
            'web/static/src/js/public/public_root_instance.js',
            # new module 
            'web/static/src/js/public/public_widget.js',
        ],
        'web.assets_frontend': [
            # replace //t[@t-call='web._assets_frontend_minimal_js']
            ('replace', 'web._assets_frontend_minimal_js', 'web._assets_frontend_minimal_js'),
        ],
        'assets_tests': [
            # new module 
            'web/static/tests/helpers/test_utils_file.js',
        ],
        'web.tests_assets': [
            # new module 
            'web/static/lib/daterangepicker/daterangepicker.css',
            # new module 
            'web/static/lib/qunit/qunit-2.9.1.css',
            # new module 
            'web/static/lib/qunit/qunit-2.9.1.js',
            # new module 
            'web/static/tests/helpers/qunit_config.js',
            # new module 
            'web/static/tests/helpers/qunit_asserts.js',
            # new module 
            'web/static/lib/fullcalendar/core/main.css',
            # new module 
            'web/static/lib/fullcalendar/daygrid/main.css',
            # new module 
            'web/static/lib/fullcalendar/timegrid/main.css',
            # new module 
            'web/static/lib/fullcalendar/list/main.css',
            # new module 
            'web/static/lib/fullcalendar/core/main.js',
            # new module 
            'web/static/lib/fullcalendar/moment/main.js',
            # new module 
            'web/static/lib/fullcalendar/interaction/main.js',
            # new module 
            'web/static/lib/fullcalendar/daygrid/main.js',
            # new module 
            'web/static/lib/fullcalendar/timegrid/main.js',
            # new module 
            'web/static/lib/fullcalendar/list/main.js',
            # new module 
            'web/static/lib/ace/ace.js',
            # new module 
            'web/static/lib/ace/javascript_highlight_rules.js',
            # new module 
            'web/static/lib/ace/mode-python.js',
            # new module 
            'web/static/lib/ace/mode-xml.js',
            # new module 
            'web/static/lib/ace/mode-js.js',
            # new module 
            'web/static/lib/Chart/Chart.js',
            # new module 
            'web/static/lib/nearest/jquery.nearest.js',
            # new module 
            'web/static/lib/daterangepicker/daterangepicker.js',
            # new module 
            'web/static/src/js/libs/daterangepicker.js',
            # new module 
            'web/static/tests/main_tests.js',
            # None None
            # wtf
            # new module 
            'web/static/tests/helpers/test_utils_create.js',
            # new module 
            'web/static/tests/helpers/test_utils_control_panel.js',
            # new module 
            'web/static/tests/helpers/test_utils_dom.js',
            # new module 
            'web/static/tests/helpers/test_utils_fields.js',
            # new module 
            'web/static/tests/helpers/test_utils_file.js',
            # new module 
            'web/static/tests/helpers/test_utils_form.js',
            # new module 
            'web/static/tests/helpers/test_utils_graph.js',
            # new module 
            'web/static/tests/helpers/test_utils_kanban.js',
            # new module 
            'web/static/tests/helpers/test_utils_mock.js',
            # new module 
            'web/static/tests/helpers/test_utils_modal.js',
            # new module 
            'web/static/tests/helpers/test_utils_pivot.js',
            # new module 
            'web/static/tests/helpers/test_utils.js',
            # new module 
            'web/static/tests/helpers/mock_server.js',
            # new module 
            'web/static/tests/helpers/test_env.js',
        ],
        'web.qunit_suite_tests': [
            # new module 
            'base/static/tests/base_settings_tests.js',
            # new module 
            'web/static/tests/qweb_tests.js',
            # new module 
            'web/static/tests/mockserver_tests.js',
            # new module 
            'web/static/tests/services/crash_manager_tests.js',
            # new module 
            'web/static/tests/services/data_manager_tests.js',
            # new module 
            'web/static/tests/services/notification_service_tests.js',
            # new module 
            'web/static/tests/fields/basic_fields_tests.js',
            # new module 
            'web/static/tests/fields/field_utils_tests.js',
            # new module 
            'web/static/tests/fields/relational_fields_tests.js',
            # new module 
            'web/static/tests/fields/relational_fields/field_many2many_tests.js',
            # new module 
            'web/static/tests/fields/relational_fields/field_many2one_tests.js',
            # new module 
            'web/static/tests/fields/relational_fields/field_one2many_tests.js',
            # new module 
            'web/static/tests/fields/signature_tests.js',
            # new module 
            'web/static/tests/fields/special_fields_tests.js',
            # new module 
            'web/static/tests/fields/upgrade_fields_tests.js',
            # new module 
            'web/static/tests/views/sample_server_tests.js',
            # new module 
            'web/static/tests/views/abstract_controller_tests.js',
            # new module 
            'web/static/tests/views/abstract_view_tests.js',
            # new module 
            'web/static/tests/views/form_tests.js',
            # new module 
            'web/static/tests/views/graph_tests.js',
            # new module 
            'web/static/tests/views/list_tests.js',
            # new module 
            'web/static/tests/views/pivot_tests.js',
            # new module 
            'web/static/tests/views/kanban_tests.js',
            # new module 
            'web/static/tests/views/calendar_tests.js',
            # new module 
            'web/static/tests/views/qweb_tests.js',
            # new module 
            'web/static/tests/views/abstract_model_tests.js',
            # new module 
            'web/static/tests/views/basic_model_tests.js',
            # new module 
            'web/static/tests/views/abstract_view_banner_tests.js',
            # new module 
            'web/static/tests/views/kanban_model_tests.js',
            # new module 
            'web/static/tests/views/view_dialogs_tests.js',
            # new module 
            'web/static/tests/views/search_panel_tests.js',
            # new module 
            'web/static/tests/core/ajax_tests.js',
            # new module 
            'web/static/tests/core/registry_tests.js',
            # new module 
            'web/static/tests/core/py_utils_tests.js',
            # new module 
            'web/static/tests/core/class_tests.js',
            # new module 
            'web/static/tests/core/rpc_tests.js',
            # new module 
            'web/static/tests/core/domain_tests.js',
            # new module 
            'web/static/tests/core/data_comparison_utils_tests.js',
            # new module 
            'web/static/tests/core/math_utils_tests.js',
            # new module 
            'web/static/tests/core/mixins_tests.js',
            # new module 
            'web/static/tests/core/patch_mixin_tests.js',
            # new module 
            'web/static/tests/core/time_tests.js',
            # new module 
            'web/static/tests/core/concurrency_tests.js',
            # new module 
            'web/static/tests/core/util_tests.js',
            # new module 
            'web/static/tests/core/widget_tests.js',
            # new module 
            'web/static/tests/core/dialog_tests.js',
            # new module 
            'web/static/tests/core/owl_dialog_tests.js',
            # new module 
            'web/static/tests/core/popover_tests.js',
            # new module 
            'web/static/tests/core/dom_tests.js',
            # new module 
            'web/static/tests/chrome/action_manager_tests.js',
            # new module 
            'web/static/tests/chrome/keyboard_navigation_mixin_tests.js',
            # new module 
            'web/static/tests/chrome/menu_tests.js',
            # new module 
            'web/static/tests/chrome/user_menu_tests.js',
            # new module 
            'web/static/tests/chrome/systray_tests.js',
            # new module 
            'web/static/tests/components/custom_checkbox_tests.js',
            # new module 
            'web/static/tests/components/custom_file_input_tests.js',
            # new module 
            'web/static/tests/components/datepicker_tests.js',
            # new module 
            'web/static/tests/components/pager_tests.js',
            # new module 
            'web/static/tests/components/action_menus_tests.js',
            # new module 
            'web/static/tests/components/dropdown_menu_tests.js',
            # new module 
            'web/static/tests/control_panel/control_panel_model_extension_tests.js',
            # new module 
            'web/static/tests/control_panel/control_panel_tests.js',
            # new module 
            'web/static/tests/control_panel/comparison_menu_tests.js',
            # new module 
            'web/static/tests/control_panel/favorite_menu_tests.js',
            # new module 
            'web/static/tests/control_panel/custom_filter_item_tests.js',
            # new module 
            'web/static/tests/control_panel/filter_menu_tests.js',
            # new module 
            'web/static/tests/control_panel/custom_group_by_item_tests.js',
            # new module 
            'web/static/tests/control_panel/groupby_menu_tests.js',
            # new module 
            'web/static/tests/control_panel/search_bar_tests.js',
            # new module 
            'web/static/tests/control_panel/search_utils_tests.js',
            # new module 
            'web/static/tests/widgets/company_switcher_tests.js',
            # new module 
            'web/static/tests/widgets/data_export_tests.js',
            # new module 
            'web/static/tests/widgets/domain_selector_tests.js',
            # new module 
            'web/static/tests/widgets/model_field_selector_tests.js',
            # new module 
            'web/static/tests/widgets/rainbow_man_tests.js',
            # new module 
            'web/static/tests/tools/debug_manager_tests.js',
            # new module 
            'web/static/tests/helpers/test_utils_tests.js',
            # new module 
            'web/static/tests/owl_compatibility_tests.js',
            # new module 
            'web/static/tests/component_extension_tests.js',
        ],
        'web.qunit_mobile_suite_tests': [
            # new module 
            'web/static/lib/jquery.touchSwipe/jquery.touchSwipe.js',
            # new module 
            'web/static/tests/fields/basic_fields_mobile_tests.js',
            # new module 
            'web/static/tests/fields/relational_fields_mobile_tests.js',
            # new module 
            'web/static/tests/components/dropdown_menu_mobile_tests.js',
        ],
        'web.assets_backend_prod_only': [
            # new module 
            'web/static/src/js/main.js',
        ],
        'pdf_js_lib': [
            # new module 
            'web/static/lib/pdfjs/build/pdf.js',
            # new module 
            'web/static/lib/pdfjs/build/pdf.worker.js',
        ],
        'web.assets_backend': [
            "static/src/xml/base.xml",
            "static/src/xml/chart.xml",
            "static/src/xml/fields.xml",
            "static/src/xml/file_upload_progress_bar.xml",
            "static/src/xml/file_upload_progress_card.xml",
            "static/src/xml/kanban.xml",
            "static/src/xml/menu.xml",
            "static/src/xml/notification.xml",
            "static/src/xml/pivot.xml",
            "static/src/xml/rainbow_man.xml",
            "static/src/xml/report.xml",
            "static/src/xml/search_panel.xml",
            "static/src/xml/web_calendar.xml",
            "static/src/xml/graph.xml",
        ],
    }
}
