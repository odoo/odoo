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
        #   > web_editor.assets_legacy_wysiwyg = assets needed by components defined in the "web_editor" module.

        'web.assets_emoji': [
            'web/static/src/core/emoji_picker/emoji_data.js'
        ],
        'web.assets_backend': [
            ('include', 'web._assets_helpers'),
            ('include', 'web._assets_backend_helpers'),
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',
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

            'web/static/lib/jquery/jquery.js',
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
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/jquery.js',

            'base/static/src/css/modules.css',

            'web/static/src/core/utils/transitions.scss',
            'web/static/src/model/**/*',
            'web/static/src/search/**/*',
            'web/static/src/webclient/icons.scss', # variables required in list_controller.scss
            'web/static/src/views/**/*',
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

            'web/static/src/legacy/xml/base.xml',
            # Don't include dark mode files in light mode
            ('remove', 'web/static/src/**/*.dark.scss'),
        ],
        'web.assets_web': [
            ('include', 'web.assets_backend'),
            'web/static/src/main.js',
            'web/static/src/start.js',
        ],
        'web.assets_frontend_minimal': [
            'web/static/src/module_loader.js',
            'web/static/src/session.js',
            'web/static/src/core/browser/cookie.js',
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

            ('include', 'web._assets_bootstrap_frontend'),

            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff',
            'web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff2',
            'web/static/lib/odoo_ui_icons/style.css',
            'web/static/lib/select2/select2.css',
            'web/static/lib/select2-bootstrap-css/select2-bootstrap.css',
            'web/static/src/webclient/navbar/navbar.scss',
            'web/static/src/scss/animation.scss',
            'web/static/src/scss/base_frontend.scss',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/src/scss/mimetypes.scss',
            'web/static/src/scss/ui.scss',
            'web/static/src/views/fields/translation_dialog.scss',
            'web/static/src/views/fields/signature/signature_field.scss',

            'web/static/src/legacy/scss/ui.scss',
            'web/static/src/legacy/scss/modal.scss',

            'web/static/src/legacy/scss/lazyloader.scss',

            ('include', 'web.assets_frontend_minimal'),

            'web/static/lib/owl/owl.js',
            'web/static/lib/owl/odoo_module.js',
            'web/static/lib/jquery/jquery.js',
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
            'web/static/lib/select2/select2.js',
            'web/static/src/legacy/js/libs/bootstrap.js',
            'web/static/src/legacy/js/libs/jquery.js',
            'web/static/src/legacy/js/core/class.js',
            'web/static/src/legacy/js/core/dialog.js',
            'web/static/src/legacy/xml/dialog.xml',
            'web/static/src/legacy/js/core/dom.js',
            'web/static/src/legacy/js/core/mixins.js',
            'web/static/src/legacy/js/core/service_mixins.js',
            'web/static/src/legacy/js/core/widget.js',

            'web/static/src/env.js',
            'web/static/src/core/utils/transitions.scss',  # included early because used by other files
            # core
            'web/static/src/core/field_service.js',
            'web/static/src/core/domain.js',
            'web/static/src/core/context.js',
            'web/static/src/core/assets.js',
            'web/static/src/core/main_components_container.js',
            'web/static/src/core/transition.js',
            'web/static/src/core/currency.js',
            'web/static/src/core/template_inheritance.js',
            'web/static/src/core/templates.js',
            'web/static/src/core/anchor_scroll_prevention.js',
            'web/static/src/core/registry_hook.js',
            'web/static/src/core/macro.js',
            'web/static/src/core/orm_service.js',
            'web/static/src/core/user.js',
            'web/static/src/core/virtual_grid_hook.js',
            'web/static/src/core/name_service.js',
            'web/static/src/core/registry.js',
            # utils
            'web/static/src/core/utils/sortable_owl.js',
            'web/static/src/core/utils/classname.js',
            'web/static/src/core/utils/files.js',
            'web/static/src/core/utils/ui.js',
            'web/static/src/core/utils/strings.js',
            'web/static/src/core/utils/functions.js',
            'web/static/src/core/utils/objects.js',
            'web/static/src/core/utils/draggable_hook_builder.js',
            'web/static/src/core/utils/xml.js',
            'web/static/src/core/utils/draggable_hook_builder_owl.js',
            'web/static/src/core/utils/timing.js',
            'web/static/src/core/utils/nested_sortable.scss',
            'web/static/src/core/utils/autoresize.js',
            'web/static/src/core/utils/search.js',
            'web/static/src/core/utils/cache.js',
            'web/static/src/core/utils/reactive.js',
            'web/static/src/core/utils/render.js',
            'web/static/src/core/utils/hooks.js',
            'web/static/src/core/utils/binary.js',
            'web/static/src/core/utils/draggable_hook_builder.scss',
            'web/static/src/core/utils/transitions.scss',
            'web/static/src/core/utils/misc.js',
            'web/static/src/core/utils/patch.js',
            'web/static/src/core/utils/arrays.js',
            'web/static/src/core/utils/urls.js',
            'web/static/src/core/utils/nested_sortable.js',
            'web/static/src/core/utils/sortable_service.js',
            'web/static/src/core/utils/sortable.js',
            'web/static/src/core/utils/scrolling.js',
            'web/static/src/core/utils/concurrency.js',
            'web/static/src/core/utils/numbers.js',
            'web/static/src/core/utils/draggable.js',
            'web/static/src/core/utils/components.js',
            'web/static/src/core/utils/colors.js',
            # ui
            'web/static/src/core/ui/block_ui.scss',
            'web/static/src/core/ui/block_ui.js',
            'web/static/src/core/ui/ui_service.js',
            # install_prompt
            'web/static/src/core/install_prompt/install_prompt.xml',
            'web/static/src/core/install_prompt/install_prompt_service.js',
            'web/static/src/core/install_prompt/install_prompt.js',
            'web/static/src/core/install_prompt/install_prompt.scss',
            # autocomplete
            'web/static/src/core/autocomplete/autocomplete.js',
            'web/static/src/core/autocomplete/autocomplete.scss',
            'web/static/src/core/autocomplete/autocomplete.xml',
            # effects
            'web/static/src/core/effects/effect_service.js',
            'web/static/src/core/effects/rainbow_man.scss',
            'web/static/src/core/effects/rainbow_man.xml',
            'web/static/src/core/effects/rainbow_man.js',
            # action_swiper
            'web/static/src/core/action_swiper/action_swiper.scss',
            'web/static/src/core/action_swiper/action_swiper.js',
            'web/static/src/core/action_swiper/action_swiper.xml',
            # notebook
            'web/static/src/core/notebook/notebook.xml',
            'web/static/src/core/notebook/notebook.scss',
            'web/static/src/core/notebook/notebook.js',
            # popover
            'web/static/src/core/popover/popover_service.js',
            'web/static/src/core/popover/popover.js',
            'web/static/src/core/popover/popover_hook.js',
            'web/static/src/core/popover/popover.xml',
            'web/static/src/core/popover/popover.scss',
            # tags_list
            'web/static/src/core/tags_list/tags_list.xml',
            'web/static/src/core/tags_list/tags_list.scss',
            'web/static/src/core/tags_list/tags_list.js',
            # file_input
            'web/static/src/core/file_input/file_input.xml',
            'web/static/src/core/file_input/file_input.js',
            # debug
            'web/static/src/core/debug/debug_menu_basic.js',
            'web/static/src/core/debug/debug_utils.js',
            'web/static/src/core/debug/debug_menu.scss',
            'web/static/src/core/debug/debug_menu.xml',
            'web/static/src/core/debug/debug_menu_items.xml',
            'web/static/src/core/debug/debug_context.js',
            'web/static/src/core/debug/debug_menu_items.js',
            'web/static/src/core/debug/debug_providers.js',
            # confirmation_dialog
            'web/static/src/core/confirmation_dialog/confirmation_dialog.xml',
            'web/static/src/core/confirmation_dialog/confirmation_dialog.js',
            # expression_editor_dialog
            'web/static/src/core/expression_editor_dialog/expression_editor_dialog.xml',
            'web/static/src/core/expression_editor_dialog/expression_editor_dialog.js',
            # domain_selector_dialog
            'web/static/src/core/domain_selector_dialog/domain_selector_dialog.js',
            'web/static/src/core/domain_selector_dialog/domain_selector_dialog.xml',
            # dialog
            'web/static/src/core/dialog/dialog_service.js',
            'web/static/src/core/dialog/dialog.xml',
            'web/static/src/core/dialog/dialog.scss',
            'web/static/src/core/dialog/dialog.js',
            # domain_selector
            'web/static/src/core/domain_selector/domain_selector.xml',
            'web/static/src/core/domain_selector/domain_selector.js',
            'web/static/src/core/domain_selector/utils.js',
            'web/static/src/core/domain_selector/domain_selector_operator_editor.js',
            # notification
            'web/static/src/core/notifications/notification.js',
            'web/static/src/core/notifications/notification.xml',
            'web/static/src/core/notifications/notification_container.js',
            'web/static/src/core/notifications/notification.variables.scss',
            'web/static/src/core/notifications/notification.scss',
            'web/static/src/core/notifications/notification_service.js',
            # dropdown
            'web/static/src/core/dropdown/dropdown_item.js',
            'web/static/src/core/dropdown/dropdown_group.js',
            'web/static/src/core/dropdown/accordion_item.js',
            'web/static/src/core/dropdown/dropdown_hooks.js',
            'web/static/src/core/dropdown/accordion_item.xml',
            'web/static/src/core/dropdown/dropdown_item.xml',
            'web/static/src/core/dropdown/dropdown.scss',
            'web/static/src/core/dropdown/dropdown.js',
            'web/static/src/core/dropdown/checkbox_item.js',
            'web/static/src/core/dropdown/accordion_item.scss',
            'web/static/src/core/dropdown/_behaviours/dropdown_nesting.js',
            'web/static/src/core/dropdown/_behaviours/dropdown_group_hook.js',
            'web/static/src/core/dropdown/_behaviours/dropdown_popover.js',
            # signature
            'web/static/src/core/signature/name_and_signature.scss',
            'web/static/src/core/signature/signature_dialog.js',
            'web/static/src/core/signature/name_and_signature.js',
            'web/static/src/core/signature/signature_dialog.xml',
            'web/static/src/core/signature/name_and_signature.xml',
            # checkbox
            'web/static/src/core/checkbox/checkbox.scss',
            'web/static/src/core/checkbox/checkbox.js',
            'web/static/src/core/checkbox/checkbox.xml',
            # expression_editor
            'web/static/src/core/expression_editor/expression_editor.xml',
            'web/static/src/core/expression_editor/expression_editor_operator_editor.js',
            'web/static/src/core/expression_editor/expression_editor.js',
            # errors
            'web/static/src/core/errors/error_service.js',
            'web/static/src/core/errors/error_dialogs.xml',
            'web/static/src/core/errors/error_utils.js',
            'web/static/src/core/errors/scss_error_dialog.js',
            'web/static/src/core/errors/error_dialog.scss',
            'web/static/src/core/errors/error_handlers.js',
            'web/static/src/core/errors/error_dialogs.js',
            # position
            'web/static/src/core/position/position_hook.js',
            'web/static/src/core/position/utils.js',
            # resizable_panel
            'web/static/src/core/resizable_panel/resizable_panel.scss',
            'web/static/src/core/resizable_panel/resizable_panel.xml',
            'web/static/src/core/resizable_panel/resizable_panel.js',
            # tree_editor
            'web/static/src/core/tree_editor/tree_editor.scss',
            'web/static/src/core/tree_editor/tree_editor.js',
            'web/static/src/core/tree_editor/tree_editor_autocomplete.js',
            'web/static/src/core/tree_editor/utils.js',
            'web/static/src/core/tree_editor/tree_editor_operator_editor.js',
            'web/static/src/core/tree_editor/condition_tree.js',
            'web/static/src/core/tree_editor/tree_editor.xml',
            'web/static/src/core/tree_editor/tree_editor_components.xml',
            'web/static/src/core/tree_editor/tree_editor_value_editors.js',
            'web/static/src/core/tree_editor/tree_editor_components.js',
            # pager
            'web/static/src/core/pager/pager.js',
            'web/static/src/core/pager/pager.xml',
            # l10n
            'web/static/src/core/l10n/dates.js',
            'web/static/src/core/l10n/localization.js',
            'web/static/src/core/l10n/utils.js',
            'web/static/src/core/l10n/localization_service.js',
            'web/static/src/core/l10n/translation.js',
            # select_menu
            'web/static/src/core/select_menu/select_menu.scss',
            'web/static/src/core/select_menu/select_menu.js',
            'web/static/src/core/select_menu/select_menu.xml',
            # overlay
            'web/static/src/core/overlay/overlay_container.js',
            'web/static/src/core/overlay/overlay_container.xml',
            'web/static/src/core/overlay/overlay_service.js',
            # model_selector
            'web/static/src/core/model_selector/model_selector.js',
            'web/static/src/core/model_selector/model_selector.xml',
            'web/static/src/core/model_selector/model_selector.scss',
            # file_viewer
            'web/static/src/core/file_viewer/file_viewer.xml',
            'web/static/src/core/file_viewer/file_viewer.scss',
            'web/static/src/core/file_viewer/file_viewer_hook.js',
            'web/static/src/core/file_viewer/file_viewer.js',
            'web/static/src/core/file_viewer/file_model.js',
            # emoji_picker
            'web/static/src/core/emoji_picker/emoji_picker.scss',
            'web/static/src/core/emoji_picker/emoji_picker.xml',
            'web/static/src/core/emoji_picker/emoji_picker.js',
            'web/static/src/core/emoji_picker/emoji_picker.dark.scss',
            # file_upload
            'web/static/src/core/file_upload/file_upload_progress_bar.scss',
            'web/static/src/core/file_upload/file_upload_progress_container.xml',
            'web/static/src/core/file_upload/file_upload_progress_bar.js',
            'web/static/src/core/file_upload/file_upload_progress_record.js',
            'web/static/src/core/file_upload/file_upload_progress_record.scss',
            'web/static/src/core/file_upload/file_upload_progress_container.js',
            'web/static/src/core/file_upload/file_upload_service.js',
            'web/static/src/core/file_upload/file_upload_progress_record.xml',
            'web/static/src/core/file_upload/file_upload_progress_bar.xml',
            # model_field_selector
            'web/static/src/core/model_field_selector/model_field_selector_popover.scss',
            'web/static/src/core/model_field_selector/model_field_selector.xml',
            'web/static/src/core/model_field_selector/model_field_selector.scss',
            'web/static/src/core/model_field_selector/model_field_selector.js',
            'web/static/src/core/model_field_selector/model_field_selector_popover.js',
            'web/static/src/core/model_field_selector/utils.js',
            'web/static/src/core/model_field_selector/model_field_selector_popover.xml',
            # browser
            'web/static/src/core/browser/feature_detection.js',
            'web/static/src/core/browser/browser.js',
            'web/static/src/core/browser/cookie.js',
            'web/static/src/core/browser/title_service.js',
            'web/static/src/core/browser/router.js',
            # tooltip
            'web/static/src/core/tooltip/tooltip.xml',
            'web/static/src/core/tooltip/tooltip.js',
            'web/static/src/core/tooltip/tooltip_service.js',
            'web/static/src/core/tooltip/tooltip.scss',
            'web/static/src/core/tooltip/tooltip_hook.js',
            # commands
            'web/static/src/core/commands/default_providers.js',
            'web/static/src/core/commands/command_palette.js',
            # code_editor
            'web/static/src/core/code_editor/code_editor.js',
            'web/static/src/core/code_editor/code_editor.xml',
            # colorpicker
            'web/static/src/core/colorpicker/colorpicker.js',
            'web/static/src/core/colorpicker/colorpicker.scss',
            'web/static/src/core/colorpicker/colorpicker.xml',
            # colors
            'web/static/src/core/colors/colors.js',
            # hotkeys
            'web/static/src/core/hotkeys/hotkey_service.js',
            'web/static/src/core/hotkeys/hotkey_hook.js',
            # network
            'web/static/src/core/network/download.js',
            'web/static/src/core/network/http_service.js',
            'web/static/src/core/network/rpc.js',
            # record_selectors
            'web/static/src/core/record_selectors/record_selector.xml',
            'web/static/src/core/record_selectors/record_autocomplete.xml',
            'web/static/src/core/record_selectors/record_selector.js',
            'web/static/src/core/record_selectors/record_autocomplete.js',
            'web/static/src/core/record_selectors/multi_record_selector.xml',
            'web/static/src/core/record_selectors/tag_navigation_hook.js',
            'web/static/src/core/record_selectors/multi_record_selector.js',
            # navigation
            'web/static/src/core/navigation/navigation.js',
            # copy_button
            'web/static/src/core/copy_button/copy_button.js',
            'web/static/src/core/copy_button/copy_button.xml',
            # py_js
            'web/static/src/core/py_js/py_tokenizer.js',
            'web/static/src/core/py_js/py_utils.js',
            'web/static/src/core/py_js/py_date.js',
            'web/static/src/core/py_js/py_parser.js',
            'web/static/src/core/py_js/py_builtin.js',
            'web/static/src/core/py_js/py_interpreter.js',
            'web/static/src/core/py_js/py.js',
            # datetime
            'web/static/src/core/datetime/datetime_picker_popover.xml',
            'web/static/src/core/datetime/datetime_input.js',
            'web/static/src/core/datetime/datetime_picker.xml',
            'web/static/src/core/datetime/datetime_hook.js',
            'web/static/src/core/datetime/datetime_input.xml',
            'web/static/src/core/datetime/datetimepicker_service.js',
            'web/static/src/core/datetime/datetime_picker.js',
            'web/static/src/core/datetime/datetime_picker_popover.js',
            'web/static/src/core/datetime/datetime_picker.scss',
            # colorlist
            'web/static/src/core/colorlist/colorlist.xml',
            'web/static/src/core/colorlist/colorlist.js',
            'web/static/src/core/colorlist/colorlist.scss',
            # avatar
            'web/static/src/core/avatar/avatar.scss',
            'web/static/src/core/avatar/avatar.variables.scss',
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
            ('remove', 'web/static/src/legacy/js/public/lazyloader.js'),
        ],
        'web.report_assets_common': [
            ('include', 'web._assets_helpers'),

            'web/static/src/webclient/actions/reports/bootstrap_overridden_report.scss',
            'web/static/src/scss/pre_variables.scss',
            'web/static/lib/bootstrap/scss/_variables.scss',

            ('include', 'web._assets_bootstrap_backend'),

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

            'base/static/src/css/description.css',
            'web/static/src/libs/fontawesome/css/font-awesome.css',
            'web/static/src/scss/fontawesome_overridden.scss',
            'web/static/lib/odoo_ui_icons/*',
            'web/static/fonts/fonts.scss',

            'web/static/src/webclient/actions/reports/report.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_standard.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_background.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_boxed.scss',
            'web/static/src/webclient/actions/reports/layout_assets/layout_clean.scss',
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
        'web._assets_bootstrap': [
            'web/static/src/scss/import_bootstrap.scss',
            'web/static/src/scss/helpers_backport.scss',
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
            # No tours are defined in web, but the bundle "assets_tests" is
            # first called in web.
            'web/static/tests/legacy/helpers/cleanup.js',
            'web/static/tests/legacy/helpers/utils.js',
            'web/static/tests/legacy/utils.js',
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
            ('remove', 'web/static/lib/hoot/tests/**/*'),

            # Odoo mocks
            # ! must be loaded before other @web assets
            'web/static/tests/_framework/mock_module_loader.js',

            # Assets for features to test (views, services, fields, ...)
            # Typically includes most files in 'web.web.assets_backend'
            ('include', 'web.assets_backend'),
        ],
        # Unit test files
        'web.assets_unit_tests': [
            'web/static/tests/**/*',

            ('remove', 'web/static/tests/_framework/mock_module_loader.js'),
            ('remove', 'web/static/tests/legacy/**/*'), # to remove when all legacy tests are ported
        ],
        'web.tests_assets': [
            ('include', 'web.assets_backend'),

            'web/static/src/public/public_component_service.js',
            'web/static/tests/legacy/patch_translations.js',
            'web/static/lib/qunit/qunit-2.9.1.css',
            'web/static/lib/qunit/qunit-2.9.1.js',
            'web/static/tests/legacy/legacy_tests/helpers/**/*',
            ('remove', 'web/static/tests/legacy/legacy_tests/helpers/test_utils_tests.js'),

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
            'web/static/tests/legacy/env_tests.js',
            'web/static/tests/legacy/reactivity_tests.js',
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
