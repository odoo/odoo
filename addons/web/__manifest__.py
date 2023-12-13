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
        'views/speedscope_template.xml',
        'views/lazy_assets.xml',
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
        #   > web.assets_common = assets common to backend clients and others
        #     (not frontend).
        #   > web_editor.assets_wysiwyg = assets needed by components defined in the "web_editor" module.

        # Warning: Layouts using "assets_frontend" assets do not have the
        # "assets_common" assets anymore. So, if it make sense, files added in
        # "assets_common" should also be added in "assets_frontend".
        # TODO in the future, probably remove "assets_common" definition
        # entirely and let all "main" bundles evolve on their own, including the
        # files they need in their bundle.
        'web.assets_common': [
            ('include', 'web._assets_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            'web/static/src/legacy/scss/tempusdominus_overridden.scss',
            'web/static/lib/tempusdominus/tempusdominus.scss',
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/lib/daterangepicker/daterangepicker.css',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/legacy/scss/ui.scss',
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
            'web/static/src/legacy/scss/fontawesome_overridden.scss',

            'web/static/src/legacy/js/promise_extension.js',
            'web/static/src/boot.js',
            'web/static/src/session.js',
            'web/static/src/legacy/js/core/cookie_utils.js',

            'web/static/lib/underscore/underscore.js',
            'web/static/lib/underscore.string/lib/underscore.string.js',
            'web/static/lib/moment/moment.js',
            'web/static/lib/luxon/luxon.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/src/owl2_compatibility/*.js',
            'web/static/src/legacy/js/component_extension.js',
            'web/static/src/legacy/legacy_component.js',
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
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
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
            'web/static/lib/tempusdominus/tempusdominus.js',
            'web/static/lib/select2/select2.js',
            'web/static/lib/clipboard/clipboard.js',
            'web/static/lib/jSignature/jSignatureCustom.js',
            'web/static/lib/qweb/qweb2.js',
            'web/static/src/legacy/js/assets.js',
            'web/static/src/legacy/js/libs/autocomplete.js',
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/content-disposition.js',
            'web/static/src/legacy/js/libs/download.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web/static/src/legacy/js/libs/moment.js',
            'web/static/src/legacy/js/libs/underscore.js',
            'web/static/src/legacy/js/libs/pdfjs.js',
            'web/static/src/legacy/js/libs/zoomodoo.js',
            'web/static/src/legacy/js/libs/jSignatureCustom.js',
            'web/static/src/legacy/js/core/abstract_service.js',
            'web/static/src/legacy/js/core/abstract_storage_service.js',
            'web/static/src/legacy/js/core/ajax.js',
            'web/static/src/legacy/js/core/browser_detection.js',
            'web/static/src/legacy/js/core/bus.js',
            'web/static/src/legacy/js/core/class.js',
            'web/static/src/legacy/js/core/collections.js',
            'web/static/src/legacy/js/core/concurrency.js',
            'web/static/src/legacy/js/core/dialog.js',
            'web/static/src/legacy/xml/dialog.xml',
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
            'web/static/src/legacy/js/services/session_storage_service.js',
            'web/static/src/legacy/js/common_env.js',
            'web/static/src/legacy/js/widgets/name_and_signature.js',
            'web/static/src/legacy/xml/name_and_signature.xml',
            'web/static/src/legacy/js/core/smooth_scroll_on_drag.js',
            'web/static/src/legacy/js/widgets/colorpicker.js',
            'web/static/src/legacy/xml/colorpicker.xml',
            'web/static/src/legacy/js/widgets/translation_dialog.js',
            'web/static/src/legacy/xml/translation_dialog.xml',
        ],
        'web.assets_backend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),

            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap'),

            'base/static/src/css/modules.css',

            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/**/*',
            'web/static/src/search/**/*',
            'web/static/src/webclient/icons.scss', # variables required in list_controller.scss
            'web/static/src/views/**/*',
            'web/static/src/webclient/**/*',
            ('remove', 'web/static/src/webclient/navbar/navbar.scss'),  # already in assets_common
            ('remove', 'web/static/src/webclient/clickbot/clickbot.js'), # lazy loaded
            ('remove', 'web/static/src/views/form/button_box/*.scss'),

            # remove the report code and whitelist only what's needed
            ('remove', 'web/static/src/webclient/actions/reports/**/*'),
            'web/static/src/webclient/actions/reports/*.js',
            'web/static/src/webclient/actions/reports/*.xml',

            'web/static/src/env.js',

            'web/static/lib/jquery.scrollTo/jquery.scrollTo.js',
            'web/static/lib/py.js/lib/py.js',
            'web/static/lib/py.js/lib/py_extras.js',
            'web/static/lib/jquery.ba-bbq/jquery.ba-bbq.js',

            'web/static/src/legacy/scss/domain_selector.scss',
            'web/static/src/legacy/scss/model_field_selector.scss',
            'web/static/src/legacy/scss/dropdown.scss',
            'web/static/src/legacy/scss/tooltip.scss',
            'web/static/src/legacy/scss/switch_company_menu.scss',
            'web/static/src/legacy/scss/ace.scss',
            'web/static/src/legacy/scss/fields.scss',
            'web/static/src/legacy/scss/views.scss',
            'web/static/src/legacy/scss/form_view.scss',
            'web/static/src/legacy/scss/list_view.scss',
            'web/static/src/legacy/scss/kanban_dashboard.scss',
            'web/static/src/legacy/scss/kanban_examples_dialog.scss',
            'web/static/src/legacy/scss/kanban_column_progressbar.scss',
            'web/static/src/legacy/scss/kanban_view.scss',
            'web/static/src/legacy/scss/data_export.scss',
            'base/static/src/scss/onboarding.scss',
            'web/static/src/legacy/scss/attachment_preview.scss',
            'web/static/src/legacy/scss/base_document_layout.scss',
            'web/static/src/legacy/scss/special_fields.scss',
            'web/static/src/legacy/scss/fields_extra.scss',
            'web/static/src/legacy/scss/form_view_extra.scss',
            'web/static/src/legacy/scss/list_view_extra.scss',
            'web/static/src/legacy/scss/color_picker.scss',
            'base/static/src/scss/res_partner.scss',

            # Form style should be computed before
            'web/static/src/views/form/button_box/*.scss',

            'web/static/src/legacy/action_adapters.js',
            'web/static/src/legacy/debug_manager.js',
            'web/static/src/legacy/legacy_service_provider.js',
            'web/static/src/legacy/legacy_client_actions.js',
            'web/static/src/legacy/legacy_dialog.js',
            'web/static/src/legacy/legacy_load_views.js',
            'web/static/src/legacy/legacy_views.js',
            'web/static/src/legacy/legacy_promise_error_handler.js',
            'web/static/src/legacy/legacy_rpc_error_handler.js',
            'web/static/src/legacy/root_widget.js',
            'web/static/src/legacy/systray_menu.js',
            'web/static/src/legacy/systray_menu_item.js',
            'web/static/src/legacy/backend_utils.js',
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
            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/fields/*',
            'web/static/src/legacy/js/services/data_manager.js',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/tools/tools.js',
            'web/static/src/legacy/js/views/**/*',
            'web/static/src/legacy/js/widgets/data_export.js',
            'web/static/src/legacy/js/widgets/date_picker.js',
            'web/static/src/legacy/js/widgets/domain_selector_dialog.js',
            'web/static/src/legacy/js/widgets/domain_selector.js',
            'web/static/src/legacy/js/widgets/iframe_widget.js',
            'web/static/src/legacy/js/widgets/model_field_selector.js',
            'web/static/src/legacy/js/widgets/model_field_selector_popover.js',
            'web/static/src/legacy/js/widgets/ribbon.js',
            'web/static/src/legacy/js/widgets/week_days.js',
            'web/static/src/legacy/js/widgets/signature.js',
            'web/static/src/legacy/js/widgets/attach_document.js',
            'web/static/src/legacy/js/apps.js',
            'web/static/src/legacy/js/env.js',
            'web/static/src/legacy/js/model.js',
            'web/static/src/legacy/js/owl_compatibility.js',

            'web/static/src/legacy/xml/base.xml',
            'web/static/src/legacy/xml/ribbon.xml',
            'web/static/src/legacy/xml/control_panel.xml',
            'web/static/src/legacy/xml/fields.xml',
            'web/static/src/legacy/xml/kanban.xml',
            'web/static/src/legacy/xml/search_panel.xml',
            'web/static/src/legacy/xml/week_days.xml',
            # Don't include dark mode files in light mode
            ('remove', 'web/static/src/**/*.dark.scss'),
        ],
        "web.assets_backend_legacy_lazy": [
            ("include", "web._assets_helpers"),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
        ],
        'web.assets_frontend_minimal': [
            'web/static/src/legacy/js/promise_extension.js',
            'web/static/src/boot.js',
            'web/static/src/session.js',
            'web/static/src/legacy/js/core/cookie_utils.js',
            'web/static/src/legacy/js/core/menu.js',
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
            'web/static/lib/luxon/luxon.js',

            ('include', 'web._assets_bootstrap'),

            'web/static/src/legacy/scss/tempusdominus_overridden.scss',
            'web/static/lib/tempusdominus/tempusdominus.scss',
            'web/static/lib/jquery.ui/jquery-ui.css',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/lib/daterangepicker/daterangepicker.css',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/legacy/scss/ui.scss',
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
            'web/static/src/legacy/scss/fontawesome_overridden.scss',

            'web/static/src/legacy/scss/base_frontend.scss',
            'web/static/src/legacy/scss/lazyloader.scss',

            ('include', 'web.assets_frontend_minimal'),

            'web/static/lib/underscore/underscore.js',
            'web/static/lib/underscore.string/lib/underscore.string.js',
            'web/static/lib/moment/moment.js',
            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/src/owl2_compatibility/*.js',
            'web/static/src/legacy/js/component_extension.js',
            'web/static/src/legacy/legacy_component.js',
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
            'web/static/lib/bootstrap/js/dist/dom/data.js',
            'web/static/lib/bootstrap/js/dist/dom/event-handler.js',
            'web/static/lib/bootstrap/js/dist/dom/manipulator.js',
            'web/static/lib/bootstrap/js/dist/dom/selector-engine.js',
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
            'web/static/lib/tempusdominus/tempusdominus.js',
            'web/static/lib/select2/select2.js',
            'web/static/lib/clipboard/clipboard.js',
            'web/static/lib/jSignature/jSignatureCustom.js',
            'web/static/lib/qweb/qweb2.js',
            'web/static/src/legacy/js/assets.js',
            'web/static/src/legacy/js/libs/autocomplete.js',
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/content-disposition.js',
            'web/static/src/legacy/js/libs/download.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web/static/src/legacy/js/libs/moment.js',
            'web/static/src/legacy/js/libs/underscore.js',
            'web/static/src/legacy/js/libs/pdfjs.js',
            'web/static/src/legacy/js/libs/zoomodoo.js',
            'web/static/src/legacy/js/libs/jSignatureCustom.js',
            'web/static/src/legacy/js/core/abstract_service.js',
            'web/static/src/legacy/js/core/abstract_storage_service.js',
            'web/static/src/legacy/js/core/ajax.js',
            'web/static/src/legacy/js/core/browser_detection.js',
            'web/static/src/legacy/js/core/bus.js',
            'web/static/src/legacy/js/core/class.js',
            'web/static/src/legacy/js/core/collections.js',
            'web/static/src/legacy/js/core/concurrency.js',
            'web/static/src/legacy/js/core/dialog.js',
            'web/static/src/legacy/xml/dialog.xml',
            'web/static/src/legacy/js/core/owl_dialog.js',
            'web/static/src/legacy/js/core/popover.js',
            'web/static/src/legacy/js/core/dom.js',
            'web/static/src/legacy/js/core/local_storage.js',
            'web/static/src/legacy/js/core/menu.js',
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
            'web/static/src/legacy/js/services/session_storage_service.js',
            'web/static/src/legacy/js/common_env.js',
            'web/static/src/legacy/js/widgets/name_and_signature.js',
            'web/static/src/legacy/xml/name_and_signature.xml',
            'web/static/src/legacy/js/core/smooth_scroll_on_drag.js',
            'web/static/src/legacy/js/widgets/colorpicker.js',
            'web/static/src/legacy/xml/colorpicker.xml',
            'web/static/src/legacy/js/widgets/translation_dialog.js',
            'web/static/src/legacy/xml/translation_dialog.xml',

            'web/static/src/env.js',
            'web/static/src/core/utils/transitions.scss',  # included early because used by other files
            'web/static/src/core/**/*',
            ('remove', 'web/static/src/core/commands/**/*'),
            ('remove', 'web/static/src/core/debug/debug_menu.js'),
            'web/static/src/public/error_notifications.js',

            'web/static/src/legacy/utils.js',
            'web/static/src/legacy/js/core/misc.js',
            'web/static/src/legacy/js/owl_compatibility.js',
            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/public/public_env.js',
            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/public_root_instance.js',
            'web/static/src/legacy/js/public/public_widget.js',
            'web/static/src/legacy/legacy_promise_error_handler.js',
            'web/static/src/legacy/legacy_rpc_error_handler.js',
            'web/static/src/legacy/js/fields/field_utils.js',

            ('include', 'web.frontend_legacy'),
        ],
        'web.assets_frontend_lazy': [
            ('include', 'web.assets_frontend'),
            # Remove assets_frontend_minimal
            ('remove', 'web/static/src/legacy/js/promise_extension.js'),
            ('remove', 'web/static/src/boot.js'),
            ('remove', 'web/static/src/session.js'),
            ('remove', 'web/static/src/legacy/js/core/cookie_utils.js'),
            ('remove', 'web/static/src/legacy/js/core/menu.js'),
            ('remove', 'web/static/src/legacy/js/public/lazyloader.js'),
        ],
        'web.assets_backend_prod_only': [
            'web/static/src/main.js',
            'web/static/src/start.js',
            'web/static/src/legacy/legacy_setup.js',
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

            'web/static/src/webclient/actions/reports/bootstrap_overridden_report.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap'),

            'base/static/src/css/description.css',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/fonts/fonts.scss',

            'web/static/src/webclient/actions/reports/report.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_standard.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_background.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_boxed.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_clean.scss',
            'web/static/asset_styles_company_report.scss',

            'web/static/src/legacy/js/services/session.js',
            'web/static/src/legacy/js/public/public_root.js',
            'web/static/src/legacy/js/public/public_root_instance.js',
            'web/static/src/legacy/js/public/public_widget.js',
            'web/static/src/legacy/js/report/report.js',
        ],
        'web.report_assets_pdf': [
            'web/static/src/webclient/actions/reports/reset.min.css',
        ],

        # ---------------------------------------------------------------------
        # COLOR SCHEME BUNDLES
        # ---------------------------------------------------------------------
        "web.dark_mode_assets_common": [
            ('include', 'web.assets_common'),
        ],
        "web.dark_mode_assets_backend": [
            ('include', 'web.assets_backend'),
            'web/static/src/**/*.dark.scss',
        ],
        "web.dark_mode_variables": [
            ('before', 'base/static/src/scss/onboarding.variables.scss', 'base/static/src/scss/onboarding.variables.dark.scss'),
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
        # Examples:
        #   > web._assets_helpers = define assets needed in most main bundles

        'web._assets_primary_variables': [
            'web/static/src/scss/primary_variables.scss',
            'web/static/src/**/**/*.variables.scss',
            'base/static/src/scss/onboarding.variables.scss',
        ],
        'web._assets_secondary_variables': [
            'web/static/src/scss/secondary_variables.scss',
        ],
        'web._assets_helpers': [
            'web/static/lib/bootstrap/scss/_functions.scss',
            'web/static/lib/bootstrap/scss/_mixins.scss',
            'web/static/src/scss/mixins_forwardport.scss',
            'web/static/src/scss/bs_mixins_overrides.scss',
            'web/static/src/legacy/scss/utils.scss',

            ('include', 'web._assets_primary_variables'),
            ('include', 'web._assets_secondary_variables'),
        ],
        'web._assets_bootstrap': [
            'web/static/src/scss/import_bootstrap.scss',
            'web/static/src/scss/helpers_backport.scss',
            'web/static/src/scss/utilities_custom.scss',
            'web/static/lib/bootstrap/scss/utilities/_api.scss',
            'web/static/src/scss/bootstrap_review.scss',
        ],
        'web._assets_backend_helpers': [
            'web/static/src/scss/bootstrap_overridden.scss',
            'web/static/src/scss/bs_mixins_overrides_backend.scss',
        ],
        'web._assets_frontend_helpers': [
            'web/static/src/scss/bootstrap_overridden_frontend.scss',
        ],

        # Used during the transition of the web architecture
        'web.frontend_legacy': [
            'web/static/src/legacy/frontend/**/*',
        ],

        # ---------------------------------------------------------------------
        # TESTS BUNDLES
        # ---------------------------------------------------------------------

        'web.assets_tests': [
            # No tours are defined in web, but the bundle "assets_tests" is
            # first called in web.
            'web/static/tests/legacy/helpers/test_utils_file.js',
            'web/static/tests/helpers/cleanup.js',
            'web/static/tests/helpers/utils.js',
            'web/static/tests/utils.js',
        ],
        # remove this bundle alongside the owl2 compatibility layer
        'web.tests_assets_common': [
            ('include', 'web.assets_common'),
            ('after', 'web/static/src/owl2_compatibility/app.js', 'web/static/tests/owl2_compatibility_app.js'),
        ],
        'web.tests_assets': [
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/helpers/**/*',
            ('remove', 'web/static/tests/legacy/helpers/test_utils_tests.js'),
            'web/static/tests/legacy/legacy_setup.js',

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
            'web/static/lib/fullcalendar/luxon/main.js',

            'web/static/lib/zxing-library/zxing-library.js',

            'web/static/lib/ace/ace.js',
            'web/static/lib/ace/javascript_highlight_rules.js',
            'web/static/lib/ace/mode-python.js',
            'web/static/lib/ace/mode-xml.js',
            'web/static/lib/ace/mode-js.js',
            'web/static/lib/ace/mode-qweb.js',
            'web/static/lib/nearest/jquery.nearest.js',
            'web/static/lib/daterangepicker/daterangepicker.js',
            'web/static/src/legacy/js/libs/daterangepicker.js',
            'web/static/lib/stacktracejs/stacktrace.js',
            'web/static/lib/Chart/Chart.js',

            '/web/static/lib/daterangepicker/daterangepicker.js',

            # 'web/static/tests/legacy/main_tests.js',
            'web/static/tests/helpers/**/*.js',
            'web/static/tests/utils.js',
            'web/static/tests/views/helpers.js',
            'web/static/tests/search/helpers.js',
            'web/static/tests/views/calendar/helpers.js',
            'web/static/tests/webclient/**/helpers.js',
            'web/static/tests/qunit.js',
            'web/static/tests/main.js',
            'web/static/tests/mock_server_tests.js',
            'web/static/tests/setup.js',

            # These 2 lines below are taken from web.assets_frontend
            # They're required for the web.frontend_legacy to work properly
            # It is expected to add other lines coming from the web.assets_frontend
            # if we need to add more and more legacy stuff that would require other scss or js.
            ('include', 'web._assets_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web.frontend_legacy'),
            ("include", "web.assets_backend_legacy_lazy"),
        ],
        'web.qunit_suite_tests': [
            'web/static/tests/env_tests.js',
            'web/static/tests/core/**/*.js',
            'web/static/tests/search/**/*.js',
            ('remove', 'web/static/tests/search/helpers.js'),
            'web/static/tests/views/**/*.js',
            ('remove', 'web/static/tests/views/helpers.js'),
            ('remove', 'web/static/tests/views/calendar/helpers.js'),
            'web/static/tests/webclient/**/*.js',
            ('remove', 'web/static/tests/webclient/**/helpers.js'),
            'web/static/tests/legacy/**/*.js',
            ('remove', 'web/static/tests/legacy/**/*_mobile_tests.js'),
            ('remove', 'web/static/tests/legacy/**/*_benchmarks.js'),
            ('remove', 'web/static/tests/legacy/helpers/**/*.js'),
            ('remove', 'web/static/tests/legacy/legacy_setup.js'),

            ('include', 'web.frontend_legacy_tests'),
        ],
        'web.qunit_mobile_suite_tests': [
            'web/static/tests/mobile/**/*.js',

            'web/static/tests/legacy/fields/basic_fields_mobile_tests.js',
            'web/static/tests/legacy/fields/relational_fields_mobile_tests.js',
            'web/static/tests/legacy/components/dropdown_menu_mobile_tests.js',
        ],

        # Used during the transition of the web architecture
        'web.frontend_legacy_tests': [
            'web/static/tests/legacy/frontend/*.js',
        ],
    },
    'bootstrap': True,  # load translations for login screen,
    'license': 'LGPL-3',
}
