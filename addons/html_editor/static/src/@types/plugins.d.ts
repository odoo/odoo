declare module "plugins" {
    import { clean_for_save_handlers, normalize_handlers, start_edition_handlers } from "@html_editor/editor";
    import { Plugin } from "@html_editor/plugin";
    import { ResourceWithSequence } from "@html_editor/utils/resource";

    import { BaseContainerShared, invalid_for_base_container_predicates } from "@html_editor/core/base_container_plugin";
    import { added_image_handlers, after_paste_handlers, before_paste_handlers, bypass_paste_image_files, clipboard_content_processors, clipboard_text_processors, ClipboardShared, paste_text_overrides } from "@html_editor/core/clipboard_plugin";
    import { content_editable_providers, content_not_editable_providers, contenteditable_to_remove_selector, valid_contenteditable_predicates } from "@html_editor/core/content_editable_plugin";
    import { before_delete_handlers, delete_backward_line_overrides, delete_backward_overrides, delete_backward_word_overrides, delete_forward_line_overrides, delete_forward_overrides, delete_forward_word_overrides, delete_handlers, delete_range_overrides, DeleteShared, functional_empty_node_predicates, is_empty_predicates, removable_descendants_providers, system_node_selectors, unremovable_node_predicates } from "@html_editor/core/delete_plugin";
    import { DialogShared } from "@html_editor/core/dialog_plugin";
    import { after_insert_handlers, before_insert_processors, before_set_tag_handlers, DomShared, node_to_insert_processors, system_attributes, system_classes, system_style_properties, are_inlines_allowed_at_root_predicates } from "@html_editor/core/dom_plugin";
    import { format_class_predicates, format_selection_handlers, FormatShared, has_format_predicates, remove_all_formats_handlers } from "@html_editor/core/format_plugin";
    import { attribute_change_handlers, attribute_change_processors, before_add_step_handlers, before_filter_mutation_record_handlers, content_updated_handlers, external_step_added_handlers, handleNewRecords, history_cleaned_handlers, history_reset_from_steps_handlers, history_reset_handlers, history_step_processors, HistoryShared, post_redo_handlers, post_undo_handlers, restore_savepoint_handlers, savable_mutation_record_predicates, serializable_descendants_processors, set_attribute_overrides, step_added_handlers, unreversible_step_predicates } from "@html_editor/core/history_plugin";
    import { beforeinput_handlers, input_handlers } from "@html_editor/core/input_plugin";
    import { before_line_break_handlers, insert_line_break_element_overrides, LineBreakShared } from "@html_editor/core/line_break_plugin";
    import { OverlayShared } from "@html_editor/core/overlay_plugin";
    import { ProtectedNodeShared } from "@html_editor/core/protected_node_plugin";
    import { SanitizeShared } from "@html_editor/core/sanitize_plugin";
    import { double_click_overrides, fix_selection_on_editable_root_overrides, fully_selected_node_predicates, intangible_char_for_keyboard_navigation_predicates, is_node_editable_predicates, selection_leave_handlers, selectionchange_handlers, SelectionShared, targeted_nodes_processors, triple_click_overrides } from "@html_editor/core/selection_plugin";
    import { shortcuts, shorthands } from "@html_editor/core/shortcut_plugin";
    import { after_split_element_handlers, before_split_block_handlers, split_element_block_overrides, SplitShared, unsplittable_node_predicates } from "@html_editor/core/split_plugin";
    import { StyleShared } from "@html_editor/core/style_plugin";
    import { user_commands, UserCommandShared } from "@html_editor/core/user_command_plugin";

    import { BannerShared } from "@html_editor/main/banner_plugin";
    import { EmojiShared } from "@html_editor/main/emoji_plugin";
    import { feff_providers, FeffShared, legit_feff_predicates, selectors_for_feff_providers } from "@html_editor/main/feff_plugin";
    import { apply_background_color_processors, apply_color_style_overrides, color_apply_overrides, color_combination_getters, ColorShared, get_background_color_processors } from "@html_editor/main/font/color_plugin";
    import { ColorUIShared } from "@html_editor/main/font/color_ui_plugin";
    import { before_insert_within_pre_processors, font_items } from "@html_editor/main/font/font_plugin";
    import { hint_targets_providers, hints } from "@html_editor/main/hint_plugin";
    import { to_inline_code_processors } from "@html_editor/main/inline_code";
    import { paste_url_overrides } from "@html_editor/main/link/link_paste_plugin";
    import { create_link_handlers, immutable_link_selectors, is_link_editable_predicates, legit_empty_link_predicates, link_compatible_selection_predicates, link_popovers, LinkShared } from "@html_editor/main/link/link_plugin";
    import { ineligible_link_for_selection_indication_predicates, ineligible_link_for_zwnbsp_predicates, LinkSelectionShared } from "@html_editor/main/link/link_selection_plugin";
    import { paste_media_url_command_providers } from "@html_editor/main/link/powerbox_url_paste_plugin";
    import { LocalOverlayShared } from "@html_editor/main/local_overlay_plugin";
    import { ImageCropShared } from "@html_editor/main/media/image_crop_plugin";
    import { delete_image_overrides, image_name_predicates, ImageShared } from "@html_editor/main/media/image_plugin";
    import { ImagePostProcessShared, on_image_updated_handlers, process_image_post_handlers, process_image_warmup_handlers } from "@html_editor/main/media/image_post_process_plugin";
    import { closest_savable_providers, ImageSaveShared } from "@html_editor/main/media/image_save_plugin";
    import { after_save_media_dialog_handlers, media_dialog_extra_tabs, MediaShared, on_added_media_handlers, on_image_saved_handlers, on_media_dialog_saved_handlers, on_replaced_media_handlers } from "@html_editor/main/media/media_plugin";
    import { move_node_blacklist_selectors, move_node_whitelist_selectors, set_movable_element_handlers, unset_movable_element_handlers } from "@html_editor/main/movenode_plugin";
    import { layout_geometry_change_handlers } from "@html_editor/main/position_plugin";
    import { power_buttons, power_buttons_visibility_predicates } from "@html_editor/main/power_buttons_plugin";
    import { powerbox_blacklist_selectors, powerbox_categories, powerbox_items, PowerboxShared } from "@html_editor/main/powerbox/powerbox_plugin";
    import { deselect_custom_selected_nodes_handlers, TableShared } from "@html_editor/main/table/table_plugin";
    import { shift_tab_overrides, tab_overrides, TabulationShared } from "@html_editor/main/tabulation_plugin";
    import { can_display_toolbar, collapsed_selection_toolbar_predicate, toolbar_groups, toolbar_items, toolbar_namespaces, ToolbarShared } from "@html_editor/main/toolbar/toolbar_plugin";

    import { CollaborationOdooShared } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
    import { CollaborationShared, external_history_step_handlers } from "@html_editor/others/collaboration/collaboration_plugin";
    import { DynamicPlaceholderShared } from "@html_editor/others/dynamic_placeholder_plugin";
    import { EmbeddedComponentShared, mount_component_handlers, post_mount_component_handlers } from "@html_editor/others/embedded_component_plugin";

    import { _t } from "@web/core/l10n/translation.js";

    /* Misc */
    export interface CSSSelector extends String {}
    export type TranslatedString = ReturnType<typeof _t>

    /** Plugin */
    export type PluginConstructor = (typeof Plugin) & {
        static id: string;
        static dependencies: keyof SharedMethods;
    };

    export interface SharedMethods {}
    interface SharedMethods {
        // Core
        baseContainer: BaseContainerShared;
        clipboard: ClipboardShared;
        delete: DeleteShared;
        dialog: DialogShared;
        dom: DomShared;
        format: FormatShared;
        history: HistoryShared;
        lineBreak: LineBreakShared;
        overlay: OverlayShared;
        protectedNode: ProtectedNodeShared;
        sanitize: SanitizeShared;
        selection: SelectionShared;
        split: SplitShared;
        style: StyleShared;
        userCommand: UserCommandShared;

        // Main
        color: ColorShared;
        colorUi: ColorUIShared;
        link: LinkShared;
        linkSelection: LinkSelectionShared;
        media: MediaShared;
        powerbox: PowerboxShared;
        table: TableShared;
        toolbar: ToolbarShared;
        emoji: EmojiShared;
        localOverlay: LocalOverlayShared;
        tabulation: TabulationShared;
        feff: FeffShared;
        image: ImageShared;
        imageCrop: ImageCropShared;
        imagePostProcess: ImagePostProcessShared;
        banner: BannerShared;
        imageSave: ImageSaveShared;

        // Others
        collaborationOdoo: CollaborationOdooShared;
        collaboration: CollaborationShared;
        dynamicPlaceholder: DynamicPlaceholderShared;
        embeddedComponents: EmbeddedComponentShared;
    }

    export interface GlobalResources {}
    export type Resources = { [key: string]: any };
    export type ResourceDeclaration<T> = Array<T | ResourceWithSequence<T>> | T | ResourceWithSequence<T>;
    export type ResourcesTypesFactory<T> = {
        [R in keyof T]: Array<T[R][0]>;
    };
    export type ResourcesDeclarationsFactory<T> = {
        [R in keyof T]: ResourceDeclaration<T[R][0]>;
    };

    interface GlobalResources extends EditorResourcesAccess {}
    export type EditorResourcesAccess = ResourcesTypesFactory<EditorResourcesList>;
    export type EditorResources = ResourcesDeclarationsFactory<EditorResourcesAccess>;

    export interface EditorResourcesList {
        // Handlers
        added_image_handlers: added_image_handlers;
        after_insert_handlers: after_insert_handlers;
        after_paste_handlers: after_paste_handlers;
        after_save_media_dialog_handlers: after_save_media_dialog_handlers;
        after_split_element_handlers: after_split_element_handlers;
        attribute_change_handlers: attribute_change_handlers;
        before_add_step_handlers: before_add_step_handlers;
        before_delete_handlers: before_delete_handlers;
        before_filter_mutation_record_handlers: before_filter_mutation_record_handlers;
        beforeinput_handlers: beforeinput_handlers;
        before_line_break_handlers: before_line_break_handlers;
        before_paste_handlers: before_paste_handlers;
        before_split_block_handlers: before_split_block_handlers;
        before_set_tag_handlers: before_set_tag_handlers;
        clean_for_save_handlers: clean_for_save_handlers;
        create_link_handlers: create_link_handlers;
        content_updated_handlers: content_updated_handlers;
        delete_handlers: delete_handlers;
        deselect_custom_selected_nodes_handlers: deselect_custom_selected_nodes_handlers;
        external_history_step_handlers: external_history_step_handlers;
        external_step_added_handlers: external_step_added_handlers;
        format_selection_handlers: format_selection_handlers;
        handleNewRecords: handleNewRecords;
        history_cleaned_handlers: history_cleaned_handlers;
        history_reset_handlers: history_reset_handlers;
        history_reset_from_steps_handlers: history_reset_from_steps_handlers;
        input_handlers: input_handlers;
        layout_geometry_change_handlers: layout_geometry_change_handlers;
        mount_component_handlers: mount_component_handlers;
        normalize_handlers: normalize_handlers;
        on_added_media_handlers: on_added_media_handlers;
        on_image_saved_handlers: on_image_saved_handlers;
        on_image_updated_handlers: on_image_updated_handlers;
        on_media_dialog_saved_handlers: on_media_dialog_saved_handlers;
        on_replaced_media_handlers: on_replaced_media_handlers;
        post_mount_component_handlers: post_mount_component_handlers;
        post_redo_handlers: post_redo_handlers;
        post_undo_handlers: post_undo_handlers;
        process_image_warmup_handlers: process_image_warmup_handlers;
        process_image_post_handlers: process_image_post_handlers;
        remove_all_formats_handlers: remove_all_formats_handlers;
        restore_savepoint_handlers: restore_savepoint_handlers;
        selectionchange_handlers: selectionchange_handlers;
        selection_leave_handlers: selection_leave_handlers;
        set_movable_element_handlers: set_movable_element_handlers;
        start_edition_handlers: start_edition_handlers;
        step_added_handlers: step_added_handlers;
        unset_movable_element_handlers: unset_movable_element_handlers;

        // Overrides
        apply_color_style_overrides: apply_color_style_overrides;
        color_apply_overrides: color_apply_overrides;
        delete_backward_overrides: delete_backward_overrides;
        delete_backward_word_overrides: delete_backward_word_overrides;
        delete_backward_line_overrides: delete_backward_line_overrides;
        delete_forward_overrides: delete_forward_overrides;
        delete_forward_word_overrides: delete_forward_word_overrides;
        delete_forward_line_overrides: delete_forward_line_overrides;
        delete_image_overrides: delete_image_overrides;
        delete_range_overrides: delete_range_overrides;
        double_click_overrides: double_click_overrides;
        triple_click_overrides: triple_click_overrides;
        fix_selection_on_editable_root_overrides: fix_selection_on_editable_root_overrides;
        insert_line_break_element_overrides: insert_line_break_element_overrides;
        paste_text_overrides: paste_text_overrides;
        paste_url_overrides: paste_url_overrides;
        set_attribute_overrides: set_attribute_overrides;
        shift_tab_overrides: shift_tab_overrides;
        split_element_block_overrides: split_element_block_overrides;
        tab_overrides: tab_overrides;

        // Predicates
        bypass_paste_image_files: bypass_paste_image_files;
        can_display_toolbar: can_display_toolbar;
        collapsed_selection_toolbar_predicate: collapsed_selection_toolbar_predicate;
        format_class_predicates: format_class_predicates;
        fully_selected_node_predicates: fully_selected_node_predicates;
        functional_empty_node_predicates: functional_empty_node_predicates;
        has_format_predicates: has_format_predicates;
        image_name_predicates: image_name_predicates;
        ineligible_link_for_selection_indication_predicates: ineligible_link_for_selection_indication_predicates;
        ineligible_link_for_zwnbsp_predicates: ineligible_link_for_zwnbsp_predicates;
        intangible_char_for_keyboard_navigation_predicates: intangible_char_for_keyboard_navigation_predicates;
        invalid_for_base_container_predicates: invalid_for_base_container_predicates;
        is_empty_predicates: is_empty_predicates;
        is_link_editable_predicates: is_link_editable_predicates;
        is_node_editable_predicates: is_node_editable_predicates;
        legit_empty_link_predicates: legit_empty_link_predicates;
        legit_feff_predicates: legit_feff_predicates;
        link_compatible_selection_predicates: link_compatible_selection_predicates;
        power_buttons_visibility_predicates: power_buttons_visibility_predicates;
        savable_mutation_record_predicates: savable_mutation_record_predicates;
        unremovable_node_predicates: unremovable_node_predicates;
        unreversible_step_predicates: unreversible_step_predicates;
        unsplittable_node_predicates: unsplittable_node_predicates;
        valid_contenteditable_predicates: valid_contenteditable_predicates;
        are_inlines_allowed_at_root_predicates: are_inlines_allowed_at_root_predicates;

        // Processors
        apply_background_color_processors: apply_background_color_processors;
        attribute_change_processors: attribute_change_processors;
        before_insert_processors: before_insert_processors;
        before_insert_within_pre_processors: before_insert_within_pre_processors;
        clipboard_content_processors: clipboard_content_processors;
        clipboard_text_processors: clipboard_text_processors;
        get_background_color_processors: get_background_color_processors;
        history_step_processors: history_step_processors;
        node_to_insert_processors: node_to_insert_processors;
        serializable_descendants_processors: serializable_descendants_processors;
        targeted_nodes_processors: targeted_nodes_processors;
        to_inline_code_processors: to_inline_code_processors;

        // Providers
        closest_savable_providers: closest_savable_providers;
        color_combination_getters: color_combination_getters;
        content_editable_providers: content_editable_providers;
        content_not_editable_providers: content_not_editable_providers;
        feff_providers: feff_providers;
        hint_targets_providers: hint_targets_providers;
        paste_media_url_command_providers: paste_media_url_command_providers;
        removable_descendants_providers: removable_descendants_providers;
        selectors_for_feff_providers: selectors_for_feff_providers;

        // Data
        contenteditable_to_remove_selector: contenteditable_to_remove_selector;
        font_items: font_items,
        hints: hints;
        immutable_link_selectors: immutable_link_selectors;
        link_popovers: link_popovers;
        media_dialog_extra_tabs: media_dialog_extra_tabs;
        move_node_blacklist_selectors: move_node_blacklist_selectors;
        move_node_whitelist_selectors: move_node_whitelist_selectors;
        power_buttons: power_buttons;
        powerbox_blacklist_selectors: powerbox_blacklist_selectors;
        powerbox_categories: powerbox_categories;
        powerbox_items: powerbox_items;
        shortcuts: shortcuts;
        shorthands: shorthands;
        system_attributes: system_attributes;
        system_classes: system_classes;
        system_node_selectors: system_node_selectors;
        system_style_properties: system_style_properties;
        toolbar_groups: toolbar_groups;
        toolbar_items: toolbar_items;
        toolbar_namespaces: toolbar_namespaces;
        user_commands: user_commands;
    }
}
