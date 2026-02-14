declare module "plugins" {
    import { AnchorShared } from "@html_builder/core/anchor/anchor_plugin";
    import { builder_components, BuilderComponentShared } from "@html_builder/core/builder_component_plugin";
    import { builder_header_middle_buttons, builder_options, BuilderOptionsShared, change_current_options_containers_listeners, clone_disabled_reason_providers, container_title, elements_to_options_title_components, get_options_container_top_buttons, has_overlay_options, keep_overlay_options, no_parent_containers, on_restore_containers_handlers, remove_disabled_reason_providers } from "@html_builder/core/builder_options_plugin";
    import { BuilderOverlayShared } from "@html_builder/core/builder_overlay/builder_overlay_plugin";
    import { CachedModelShared } from "@html_builder/core/cached_model_plugin";
    import { CloneShared, on_cloned_handlers, on_will_clone_handlers } from "@html_builder/core/clone_plugin";
    import { CustomizeTabShared } from "@html_builder/core/customize_tab_plugin";
    import { DisableSnippetsShared } from "@html_builder/core/disable_snippets_plugin";
    import { dropzone_selector, DropZoneShared, filter_for_sibling_dropzone_predicates } from "@html_builder/core/drop_zone_plugin";
    import { after_replication_handlers } from "@html_builder/core/field_change_replication_plugin";
    import { MediaWebsiteShared } from "@html_builder/core/media_website_plugin";
    import { OperationShared } from "@html_builder/core/operation_plugin";
    import { get_overlay_buttons, OverlayButtonsShared } from "@html_builder/core/overlay_buttons/overlay_buttons_plugin";
    import { empty_node_predicates, is_unremovable_selector, on_removed_handlers, on_will_remove_handlers, RemoveShared } from "@html_builder/core/remove_plugin";
    import { after_save_handlers, before_save_handlers, get_dirty_els, pre_save_handlers, savable_selectors, save_element_handlers, save_elements_overrides, save_handlers, SaveShared } from "@html_builder/core/save_plugin";
    import { after_setup_editor_handlers, before_setup_editor_handlers, o_editable_selectors, SetupEditorShared } from "@html_builder/core/setup_editor_plugin";
    import { target_hide, target_show, VisibilityShared } from "@html_builder/core/visibility_plugin";
    import { default_shape_handlers, image_shape_groups_providers, post_compute_shape_listeners } from "@html_builder/plugins/image/image_shape_option_plugin";
    import { background_filter_target_providers, get_target_element_providers, on_bg_image_hide_handlers } from "@html_builder/plugins/background_option/background_image_option_plugin";
    import { is_draggable_handlers, on_element_dragged_handlers, on_element_dropped_handlers, on_element_dropped_near_handlers, on_element_dropped_over_handlers, on_element_move_handlers, on_element_out_dropzone_handlers, on_element_over_dropzone_handlers, on_prepare_drag_handlers } from "@html_builder/core/drag_and_drop_plugin";
    import { lower_panel_entries, on_mobile_preview_clicked, trigger_dom_updated } from "@html_builder/builder";
    import { on_reveal_target_handlers } from "@html_builder/sidebar/invisible_elements_panel";
    import { on_snippet_dragged_handlers, on_snippet_dropped_handlers, on_snippet_dropped_near_handlers, on_snippet_dropped_over_handlers, on_snippet_move_handlers, on_snippet_out_dropzone_handlers, on_snippet_over_dropzone_handlers } from "@html_builder/sidebar/block_tab";
    import { snippet_preview_dialog_bundles, snippet_preview_dialog_stylesheets_handlers } from "@html_builder/snippets/add_snippet_dialog";
    import { background_shape_groups_providers, background_shape_target_providers } from "@html_builder/plugins/background_option/background_shape_option_plugin";
    import { mark_color_level_selector_params } from "@html_builder/plugins/background_option/background_option_plugin";
    import { is_movable_selector } from "@html_builder/core/move_plugin";
    import { content_editable_selectors, content_not_editable_selectors } from "@html_builder/core/builder_content_editable_plugin";
    import { builder_actions, BuilderActionsShared } from "@html_builder/core/builder_actions_plugin";
    import { so_content_addition_selector, so_snippet_addition_selector } from "@html_builder/core/dropzone_selector_plugin";
    import { fontCssVariables } from "@html_builder/plugins/font/font_plugin";
    import { apply_custom_css_style } from "@html_builder/core/core_builder_action_plugin";

    interface SharedMethods {
        // Main

        // Core
        anchor: AnchorShared;
        builderActions: BuilderActionsShared;
        builderComponents: BuilderComponentShared;
        builderOptions: BuilderOptionsShared;
        builderOverlay: BuilderOverlayShared;
        cachedModel: CachedModelShared;
        clone: CloneShared;
        customizeTab: CustomizeTabShared;
        disableSnippets: DisableSnippetsShared;
        dropzone: DropZoneShared;
        media_website: MediaWebsiteShared;
        operation: OperationShared;
        overlayButtons: OverlayButtonsShared;
        remove: RemoveShared;
        savePlugin: SaveShared;
        setup_editor_plugin: SetupEditorShared;
        visibility: VisibilityShared;

        // Other
    }

    interface GlobalResources extends BuilderResourcesAccess {}
    export type BuilderResourcesAccess = EditorResourcesAccess & ResourcesTypesFactory<BuilderResourcesList>;
    export type BuilderResources = ResourcesDeclarationsFactory<BuilderResourcesAccess>;
    export interface BuilderResourcesList {
        // Handlers
        after_replication_handlers: after_replication_handlers;
        after_save_handlers: after_save_handlers;
        after_setup_editor_handlers: after_setup_editor_handlers;
        background_shape_groups_providers: background_shape_groups_providers;
        before_save_handlers: before_save_handlers;
        before_setup_editor_handlers: before_setup_editor_handlers;
        change_current_options_containers_listeners: change_current_options_containers_listeners;
        default_shape_handlers: default_shape_handlers;
        image_shape_groups_providers: image_shape_groups_providers;
        on_bg_image_hide_handlers: on_bg_image_hide_handlers;
        on_cloned_handlers: on_cloned_handlers;
        on_element_dragged_handlers: on_element_dragged_handlers;
        on_element_dropped_handlers: on_element_dropped_handlers;
        on_element_dropped_near_handlers: on_element_dropped_near_handlers;
        on_element_dropped_over_handlers: on_element_dropped_over_handlers;
        on_element_move_handlers: on_element_move_handlers;
        on_element_out_dropzone_handlers: on_element_out_dropzone_handlers;
        on_element_over_dropzone_handlers: on_element_over_dropzone_handlers;
        on_mobile_preview_clicked: on_mobile_preview_clicked;
        on_prepare_drag_handlers: on_prepare_drag_handlers;
        on_removed_handlers: on_removed_handlers;
        on_restore_containers_handlers: on_restore_containers_handlers;
        on_reveal_target_handlers: on_reveal_target_handlers;
        on_snippet_dragged_handlers: on_snippet_dragged_handlers;
        on_snippet_dropped_handlers: on_snippet_dropped_handlers;
        on_snippet_dropped_near_handlers: on_snippet_dropped_near_handlers;
        on_snippet_dropped_over_handlers: on_snippet_dropped_over_handlers;
        on_snippet_move_handlers: on_snippet_move_handlers;
        on_snippet_out_dropzone_handlers: on_snippet_out_dropzone_handlers;
        on_snippet_over_dropzone_handlers: on_snippet_over_dropzone_handlers;
        on_will_clone_handlers: on_will_clone_handlers;
        on_will_remove_handlers: on_will_remove_handlers;
        post_compute_shape_listeners: post_compute_shape_listeners;
        pre_save_handlers: pre_save_handlers;
        save_element_handlers: save_element_handlers;
        save_handlers: save_handlers;
        snippet_preview_dialog_stylesheets_handlers: snippet_preview_dialog_stylesheets_handlers;
        target_hide: target_hide;
        target_show: target_show;
        trigger_dom_updated: trigger_dom_updated;

        // Overrides
        apply_custom_css_style: apply_custom_css_style;
        save_elements_overrides: save_elements_overrides;

        // Predicates
        empty_node_predicates: empty_node_predicates;
        filter_for_sibling_dropzone_predicates: filter_for_sibling_dropzone_predicates;
        is_draggable_handlers: is_draggable_handlers;
        keep_overlay_options: keep_overlay_options;

        // Processors

        // Providers
        background_filter_target_providers: background_filter_target_providers;
        background_shape_target_providers: background_shape_target_providers;
        clone_disabled_reason_providers: clone_disabled_reason_providers;
        get_dirty_els: get_dirty_els;
        get_options_container_top_buttons: get_options_container_top_buttons;
        get_target_element_providers: get_target_element_providers;
        remove_disabled_reason_providers: remove_disabled_reason_providers;

        // Data
        builder_actions: builder_actions;
        builder_components: builder_components;
        builder_header_middle_buttons: builder_header_middle_buttons;
        builder_options: builder_options;
        container_title: container_title;
        content_editable_selectors: content_editable_selectors;
        content_not_editable_selectors: content_not_editable_selectors;
        dropzone_selector: dropzone_selector;
        elements_to_options_title_components: elements_to_options_title_components;
        fontCssVariables: fontCssVariables;
        get_overlay_buttons: get_overlay_buttons;
        has_overlay_options: has_overlay_options;
        is_movable_selector: is_movable_selector;
        is_unremovable_selector: is_unremovable_selector;
        lower_panel_entries: lower_panel_entries;
        mark_color_level_selector_params: mark_color_level_selector_params;
        no_parent_containers: no_parent_containers;
        o_editable_selectors: o_editable_selectors;
        /** @deprecated */
        patch_builder_options: {
            target_name: string,
            target_element: "selector" | "exclude" | "applyTo",
            method: "replace" | "add" | "remove",
            value: CSSSelector,
        }[];
        savable_selectors: savable_selectors;
        so_content_addition_selector: so_content_addition_selector;
        so_snippet_addition_selector: so_snippet_addition_selector;
        snippet_preview_dialog_bundles: snippet_preview_dialog_bundles;
    }
}
