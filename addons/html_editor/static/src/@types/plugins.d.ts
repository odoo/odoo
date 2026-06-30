declare module "plugins" {
    import { clean_for_save_processors, normalize_processors, on_editor_started_handlers } from "@html_editor/editor";
    import { Plugin } from "@html_editor/plugin";
    import { ResourceWithSequence } from "@html_editor/utils/resource";

    import { BaseContainerShared, is_valid_for_base_container_predicates } from "@html_editor/core/base_container_plugin";
    import { on_image_added_handlers, on_pasted_handlers, on_will_paste_handlers, should_bypass_paste_image_files_predicates, clipboard_content_processors, clipboard_text_processors, ClipboardShared, paste_text_overrides } from "@html_editor/core/clipboard_plugin";
    import { content_editable_providers, content_not_editable_providers, contenteditable_to_remove_selector, is_valid_contenteditable_predicates } from "@html_editor/core/content_editable_plugin";
    import { on_will_delete_handlers, delete_backward_line_overrides, delete_backward_overrides, delete_backward_word_overrides, delete_forward_line_overrides, delete_forward_overrides, delete_forward_word_overrides, on_deleted_handlers, delete_range_overrides, DeleteShared, removable_descendants_providers, system_node_selectors, is_node_removable_predicates } from "@html_editor/core/delete_plugin";
    import { DialogShared } from "@html_editor/core/dialog_plugin";
    import { DomObserverShared, attributes_mutation_value_processors, on_will_filter_mutations_handlers, set_attribute_overrides, on_content_updated_handlers, on_pending_mutations_staged_handlers, serializable_descendants_processors, on_pending_mutations_normalized_handlers, is_mutation_savable_predicates, is_classlist_mutation_savable_predicates } from "@html_editor/core/dom_observer_plugin";
    import { on_inserted_handlers, before_insert_processors, on_will_set_tag_handlers, DomShared, node_to_insert_processors, system_attributes, system_classes, system_style_properties, are_inlines_allowed_at_root_predicates } from "@html_editor/core/dom_plugin";
    import { DomReferenceMapShared } from "@html_editor/core/dom_reference_map_plugin";
    import { can_format_content_predicates, format_specs, is_format_class_predicates, before_format_handlers, formattable_node_providers, FormatShared, has_format_predicates, on_all_formats_removed_handlers, on_format_applied_handlers, on_format_requested_handlers, on_collapsed_formats_removed_handlers } from "@html_editor/core/format_plugin";
    import { HistoryShared, history_commit_data_properties, on_apply_history_commit_handlers, on_history_commit_restored_handlers, on_irreversible_history_commit_applied_handlers, on_revert_history_commit_handlers, on_committed_to_history_handlers, on_will_reset_history_handlers, on_history_commit_redone_handlers, on_history_commit_undone_handlers, on_savepoint_restored_handlers, on_will_rebase_history_handlers, on_history_rebased_handlers, on_remote_history_commit_applied_handlers, on_will_preview_handlers, on_pending_changes_unstashed_handlers, on_history_reset_handlers, on_will_invalidate_pending_changes_handlers, has_history_commit_changes_predicates, is_history_commit_reversible_predicates, pending_history_commit_data_processors, save_point_history_commit_data_processors, snapshot_history_commit_data_processors } from "@html_editor/core/history_plugin";
    import { on_beforeinput_handlers, on_input_handlers } from "@html_editor/core/input_plugin";
    import { on_will_break_line_handlers, insert_line_break_element_overrides, LineBreakShared } from "@html_editor/core/line_break_plugin";
    import { OverlayShared } from "@html_editor/core/overlay_plugin";
    import { ProtectedNodeShared } from "@html_editor/core/protected_node_plugin";
    import { region_properties, RegionShared } from "@html_editor/core/region_plugin";
    import { SanitizeShared } from "@html_editor/core/sanitize_plugin";
    import { double_click_overrides, fix_selection_on_editable_root_overrides, is_node_fully_selected_predicates, is_char_tangible_for_keyboard_navigation_predicates, on_selection_leave_handlers, on_selectionchange_handlers, SelectionShared, targeted_nodes_processors, triple_click_overrides } from "@html_editor/core/selection_plugin";
    import { shortcuts, shorthands } from "@html_editor/core/shortcut_plugin";
    import { on_element_split_handlers, on_will_split_block_handlers, split_element_block_overrides, SplitShared, is_node_splittable_predicates } from "@html_editor/core/split_plugin";
    import { StyleShared } from "@html_editor/core/style_plugin";
    import { user_commands, UserCommandShared } from "@html_editor/core/user_command_plugin";

    import { BannerShared } from "@html_editor/main/banner_plugin";
    import { EmojiShared } from "@html_editor/main/emoji_plugin";
    import { feff_providers, FeffShared, would_feff_be_legit_predicates, selectors_for_feff_providers } from "@html_editor/main/feff_plugin";
    import { apply_background_color_processors, apply_color_style_overrides, apply_color_overrides, color_combination_providers, ColorShared, background_color_processors, on_color_requested_handlers, before_color_element_processors } from "@html_editor/main/font/color_plugin";
    import { ColorUIShared, selected_background_color_providers } from "@html_editor/main/font/color_ui_plugin";
    import { before_insert_within_pre_processors, font_type_items } from "@html_editor/main/font/font_type_plugin";
    import { before_insert_within_pre_processors } from "@html_editor/main/font/font_size_plugin";
    import { hint_targets_providers } from "@html_editor/main/hint_plugin";
    import { to_inline_code_processors } from "@html_editor/main/inline_code";
    import { paste_url_overrides } from "@html_editor/main/link/link_paste_plugin";
    import { on_link_created_handlers, immutable_link_selectors, is_link_editable_predicates, is_empty_link_legit_predicates, is_link_allowed_on_selection_predicates, link_popovers, LinkShared, advanced_popover_options } from "@html_editor/main/link/link_plugin";
    import { is_link_eligible_for_visual_indication_predicates, is_link_eligible_for_zwnbsp_predicates, LinkSelectionShared } from "@html_editor/main/link/link_selection_plugin";
    import { paste_media_url_command_providers } from "@html_editor/main/link/powerbox_url_paste_plugin";
    import { LocalOverlayShared } from "@html_editor/main/local_overlay_plugin";
    import { ImageCropShared } from "@html_editor/main/media/image_crop_plugin";
    import { delete_image_overrides, image_name_providers, ImageShared } from "@html_editor/main/media/image_plugin";
    import { ImagePostProcessShared, on_image_updated_handlers, on_image_processed_handlers, on_will_process_image_handlers } from "@html_editor/main/media/image_post_process_plugin";
    import { closest_savable_providers, ImageSaveShared, on_image_saved_handlers } from "@html_editor/main/media/image_save_plugin";
    import { media_dialog_extra_tabs, MediaShared, on_media_added_handlers, on_media_dialog_saved_handlers, on_will_save_media_dialog_handlers, on_media_replaced_handlers } from "@html_editor/main/media/media_plugin";
    import { move_node_blacklist_selectors, move_node_whitelist_selectors, on_movable_element_set_handlers, on_will_unset_movable_element_handlers } from "@html_editor/main/movenode_plugin";
    import { on_layout_geometry_change_handlers } from "@html_editor/main/position_plugin";
    import { power_buttons } from "@html_editor/main/power_buttons_plugin";
    import { powerbox_blacklist_selectors, powerbox_categories, powerbox_items, PowerboxShared } from "@html_editor/main/powerbox/powerbox_plugin";
    import { deselect_custom_selected_nodes_processors, TableShared } from "@html_editor/main/table/table_plugin";
    import { shift_tab_overrides, tab_overrides, TabulationShared } from "@html_editor/main/tabulation_plugin";
    import { toolbar_groups, toolbar_items, toolbar_namespaces, ToolbarShared } from "@html_editor/main/toolbar/toolbar_plugin";

    import { CollaborationOdooShared } from "@html_editor/others/collaboration/collaboration_odoo_plugin";
    import { CollaborationShared, on_remote_history_commits_applied_handlers } from "@html_editor/others/collaboration/collaboration_plugin";
    import { DynamicPlaceholderShared } from "@html_editor/others/dynamic_placeholder_plugin";
    import { EmbeddedComponentShared, on_will_mount_component_handlers, on_component_mounted_handlers } from "@html_editor/others/embedded_component_plugin";

    /* Misc */
    export interface CSSSelector extends String {}
    export interface LazyTranslatedString extends String {}

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
        domReferenceMap: DomReferenceMapShared;
        domObserver: DomObserverShared;
        format: FormatShared;
        history: HistoryShared;
        lineBreak: LineBreakShared;
        overlay: OverlayShared;
        protectedNode: ProtectedNodeShared;
        region: RegionShared;
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
        before_format_handlers: before_format_handlers;
        on_all_formats_removed_handlers: on_all_formats_removed_handlers;
        on_apply_history_commit_handlers: on_apply_history_commit_handlers;
        on_beforeinput_handlers: on_beforeinput_handlers;
        on_collapsed_formats_removed_handlers: on_collapsed_formats_removed_handlers;
        on_color_requested_handlers: on_color_requested_handlers;
        on_committed_to_history_handlers: on_committed_to_history_handlers;
        on_component_mounted_handlers: on_component_mounted_handlers;
        on_content_updated_handlers: on_content_updated_handlers;
        on_deleted_handlers: on_deleted_handlers;
        on_editor_started_handlers: on_editor_started_handlers;
        on_element_split_handlers: on_element_split_handlers;
        on_format_applied_handlers: on_format_applied_handlers;
        on_format_requested_handlers: on_format_requested_handlers;
        on_history_commit_redone_handlers: on_history_commit_redone_handlers;
        on_history_commit_restored_handlers: on_history_commit_restored_handlers;
        on_history_commit_undone_handlers: on_history_commit_undone_handlers;
        on_history_reset_handlers: on_history_reset_handlers;
        on_history_rebased_handlers: on_history_rebased_handlers;
        on_irreversible_history_commit_applied_handlers: on_irreversible_history_commit_applied_handlers;
        on_pending_changes_unstashed_handlers: on_pending_changes_unstashed_handlers;
        on_image_added_handlers: on_image_added_handlers;
        on_image_processed_handlers: on_image_processed_handlers;
        on_image_saved_handlers: on_image_saved_handlers;
        on_image_updated_handlers: on_image_updated_handlers;
        on_input_handlers: on_input_handlers;
        on_inserted_handlers: on_inserted_handlers;
        on_layout_geometry_change_handlers: on_layout_geometry_change_handlers;
        on_link_created_handlers: on_link_created_handlers;
        on_media_added_handlers: on_media_added_handlers;
        on_media_dialog_saved_handlers: on_media_dialog_saved_handlers;
        on_media_replaced_handlers: on_media_replaced_handlers;
        on_movable_element_set_handlers: on_movable_element_set_handlers;
        on_pasted_handlers: on_pasted_handlers;
        on_pending_mutations_normalized_handlers: on_pending_mutations_normalized_handlers;
        on_pending_mutations_staged_handlers: on_pending_mutations_staged_handlers;
        on_remote_history_commit_applied_handlers: on_remote_history_commit_applied_handlers;
        on_remote_history_commits_applied_handlers: on_remote_history_commits_applied_handlers;
        on_revert_history_commit_handlers: on_revert_history_commit_handlers;
        on_savepoint_restored_handlers: on_savepoint_restored_handlers;
        on_selection_leave_handlers: on_selection_leave_handlers;
        on_selectionchange_handlers: on_selectionchange_handlers;
        on_will_delete_handlers: on_will_delete_handlers;
        on_will_break_line_handlers: on_will_break_line_handlers;
        on_will_filter_mutations_handlers: on_will_filter_mutations_handlers;
        on_will_invalidate_pending_changes_handlers: on_will_invalidate_pending_changes_handlers;
        on_will_mount_component_handlers: on_will_mount_component_handlers;
        on_will_paste_handlers: on_will_paste_handlers;
        on_will_preview_handlers: on_will_preview_handlers;
        on_will_process_image_handlers: on_will_process_image_handlers;
        on_will_rebase_history_handlers: on_will_rebase_history_handlers;
        on_will_reset_history_handlers: on_will_reset_history_handlers;
        on_will_save_media_dialog_handlers: on_will_save_media_dialog_handlers;
        on_will_set_tag_handlers: on_will_set_tag_handlers;
        on_will_split_block_handlers: on_will_split_block_handlers;
        on_will_unset_movable_element_handlers: on_will_unset_movable_element_handlers;

        // Overrides
        apply_color_style_overrides: apply_color_style_overrides;
        apply_color_overrides: apply_color_overrides;
        delete_backward_line_overrides: delete_backward_line_overrides;
        delete_backward_overrides: delete_backward_overrides;
        delete_backward_word_overrides: delete_backward_word_overrides;
        delete_forward_line_overrides: delete_forward_line_overrides;
        delete_forward_overrides: delete_forward_overrides;
        delete_forward_word_overrides: delete_forward_word_overrides;
        delete_image_overrides: delete_image_overrides;
        delete_range_overrides: delete_range_overrides;
        double_click_overrides: double_click_overrides;
        fix_selection_on_editable_root_overrides: fix_selection_on_editable_root_overrides;
        insert_line_break_element_overrides: insert_line_break_element_overrides;
        paste_text_overrides: paste_text_overrides;
        paste_url_overrides: paste_url_overrides;
        set_attribute_overrides: set_attribute_overrides;
        shift_tab_overrides: shift_tab_overrides;
        split_element_block_overrides: split_element_block_overrides;
        tab_overrides: tab_overrides;
        triple_click_overrides: triple_click_overrides;

        // Predicates
        can_format_content_predicates: can_format_content_predicates;
        has_format_predicates: has_format_predicates;
        has_history_commit_changes_predicates: has_history_commit_changes_predicates;
        is_char_tangible_for_keyboard_navigation_predicates: is_char_tangible_for_keyboard_navigation_predicates;
        is_classlist_mutation_savable_predicates: is_classlist_mutation_savable_predicates;
        is_empty_link_legit_predicates: is_empty_link_legit_predicates;
        is_format_class_predicates: is_format_class_predicates;
        is_history_commit_reversible_predicates: is_history_commit_reversible_predicates;
        is_link_allowed_on_selection_predicates: is_link_allowed_on_selection_predicates;
        is_link_editable_predicates: is_link_editable_predicates;
        is_link_eligible_for_visual_indication_predicates: is_link_eligible_for_visual_indication_predicates;
        is_link_eligible_for_zwnbsp_predicates: is_link_eligible_for_zwnbsp_predicates;
        is_mutation_savable_predicates: is_mutation_savable_predicates;
        is_node_fully_selected_predicates: is_node_fully_selected_predicates;
        is_node_removable_predicates: is_node_removable_predicates;
        is_node_splittable_predicates: is_node_splittable_predicates;
        is_valid_contenteditable_predicates: is_valid_contenteditable_predicates;
        is_valid_for_base_container_predicates: is_valid_for_base_container_predicates;
        should_bypass_paste_image_files_predicates: should_bypass_paste_image_files_predicates;
        would_feff_be_legit_predicates: would_feff_be_legit_predicates;
        are_inlines_allowed_at_root_predicates: are_inlines_allowed_at_root_predicates;

        // Processors
        apply_background_color_processors: apply_background_color_processors;
        attributes_mutation_value_processors: attributes_mutation_value_processors;
        background_color_processors: background_color_processors;
        before_color_element_processors: before_color_element_processors;
        before_insert_processors: before_insert_processors;
        before_insert_within_pre_processors: before_insert_within_pre_processors;
        clean_for_save_processors: clean_for_save_processors;
        clipboard_content_processors: clipboard_content_processors;
        clipboard_text_processors: clipboard_text_processors;
        deselect_custom_selected_nodes_processors: deselect_custom_selected_nodes_processors;
        node_to_insert_processors: node_to_insert_processors;
        normalize_processors: normalize_processors;
        pending_history_commit_data_processors: pending_history_commit_data_processors;
        save_point_history_commit_data_processors: save_point_history_commit_data_processors;
        serializable_descendants_processors: serializable_descendants_processors;
        snapshot_history_commit_data_processors: snapshot_history_commit_data_processors;
        targeted_nodes_processors: targeted_nodes_processors;
        to_inline_code_processors: to_inline_code_processors;

        // Providers
        closest_savable_providers: closest_savable_providers;
        color_combination_providers: color_combination_providers;
        content_editable_providers: content_editable_providers;
        content_not_editable_providers: content_not_editable_providers;
        feff_providers: feff_providers;
        formattable_node_providers: formattable_node_providers;
        hint_targets_providers: hint_targets_providers;
        image_name_providers: image_name_providers;
        paste_media_url_command_providers: paste_media_url_command_providers;
        removable_descendants_providers: removable_descendants_providers;
        selectors_for_feff_providers: selectors_for_feff_providers;
        selected_background_color_providers: selected_background_color_providers

        // Data
        advanced_popover_options: advanced_popover_options;
        contenteditable_to_remove_selector: contenteditable_to_remove_selector;
        font_type_items: font_type_items,
        format_specs: format_specs;
        history_commit_data_properties: history_commit_data_properties;
        immutable_link_selectors: immutable_link_selectors;
        link_popovers: link_popovers;
        media_dialog_extra_tabs: media_dialog_extra_tabs;
        move_node_blacklist_selectors: move_node_blacklist_selectors;
        move_node_whitelist_selectors: move_node_whitelist_selectors;
        power_buttons: power_buttons;
        powerbox_blacklist_selectors: powerbox_blacklist_selectors;
        powerbox_categories: powerbox_categories;
        powerbox_items: powerbox_items;
        region_properties: region_properties;
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
