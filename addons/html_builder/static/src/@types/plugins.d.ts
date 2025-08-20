declare module "plugins" {
    import { AnchorShared } from "@html_builder/core/anchor/anchor_plugin";
    import { builder_components, BuilderComponentShared } from "@html_builder/core/builder_component_plugin";
    import { builder_header_middle_buttons, builder_options_render_context, BuilderOptionsShared, on_current_options_containers_changed_handlers, clone_disabled_reason_providers, container_title, elements_to_options_title_components, options_container_top_buttons_providers, has_overlay_options, should_keep_overlay_options_predicates, no_parent_containers, on_will_restore_containers_handlers, remove_disabled_reason_providers, auto_unfold_container_providers } from "@html_builder/core/builder_options_plugin";
    import { BuilderOverlayShared } from "@html_builder/core/builder_overlay/builder_overlay_plugin";
    import { CachedModelShared } from "@html_builder/core/cached_model_plugin";
    import { CloneShared, on_cloned_handlers, on_will_clone_handlers } from "@html_builder/core/clone_plugin";
    import { CustomizeTabShared } from "@html_builder/core/customize_tab_plugin";
    import { DisableSnippetsShared } from "@html_builder/core/disable_snippets_plugin";
    import { dropzone_selectors, DropZoneShared, is_valid_for_sibling_dropzone_predicates } from "@html_builder/core/drop_zone_plugin";
    import { on_replicated_handlers } from "@html_builder/core/field_change_replication_plugin";
    import { MediaWebsiteShared } from "@html_builder/core/media_website_plugin";
    import { OperationShared } from "@html_builder/core/operation_plugin";
    import { get_overlay_buttons, OverlayButtonsShared, should_show_overlay_buttons_of_ancestor_predicates } from "@html_builder/core/overlay_buttons/overlay_buttons_plugin";
    import { is_node_empty_predicates, is_unremovable_selectors, on_removed_handlers, on_will_remove_handlers, RemoveShared } from "@html_builder/core/remove_plugin";
    import { on_saved_handlers, on_will_save_handlers, dirty_els_providers, on_will_save_element_handlers, save_elements_overrides, on_ready_to_save_document_handlers, SaveShared } from "@html_builder/core/save_plugin";
    import { after_setup_editor_overrides, on_will_setup_editor_handlers, savable_selectors, SetupEditorShared } from "@html_builder/core/setup_editor_plugin";
    import { on_target_hidden_handlers, on_target_shown_handlers, VisibilityShared } from "@html_builder/core/visibility_plugin";
    import { default_shape_providers, image_shape_groups_providers, on_shape_computed_handlers } from "@html_builder/plugins/image/image_shape_option_plugin";
    import { background_filter_target_providers, target_element_providers, on_bg_image_hidden_handlers } from "@html_builder/plugins/background_option/background_image_option_plugin";
    import { is_draggable_predicates, on_element_dragged_handlers, on_element_dropped_handlers, on_element_dropped_near_handlers, on_element_dropped_over_handlers, on_element_move_handlers, on_element_out_dropzone_handlers, on_element_over_dropzone_handlers, on_prepare_drag_handlers } from "@html_builder/core/drag_and_drop_plugin";
    import { lower_panel_entries, on_dom_updated_handlers, on_mobile_view_switched_handlers } from "@html_builder/builder";
    import { on_target_revealed_handlers } from "@html_builder/sidebar/invisible_elements_panel";
    import { on_snippet_dragged_handlers, on_snippet_dropped_handlers, on_snippet_dropped_near_handlers, on_snippet_dropped_over_handlers, on_snippet_move_handlers, on_snippet_out_dropzone_handlers, on_snippet_over_dropzone_handlers } from "@html_builder/sidebar/block_tab";
    import { snippet_preview_dialog_bundles, snippet_preview_dialog_stylesheets_processors } from "@html_builder/snippets/add_snippet_dialog";
    import { background_shape_groups_providers, background_shape_target_providers, is_element_in_invisible_panel_predicates } from "@html_builder/plugins/background_option/background_shape_option_plugin";
    import { mark_color_level_selector_params } from "@html_builder/plugins/background_option/background_option_plugin";
    import { is_movable_selectors, on_element_arrow_moved_handlers } from "@html_builder/core/move_plugin";
    import { content_editable_selectors, content_not_editable_selectors } from "@html_builder/core/builder_content_editable_plugin";
    import { builder_actions, BuilderActionsShared } from "@html_builder/core/builder_actions_plugin";
    import { so_content_addition_selectors, so_snippet_addition_selectors } from "@html_builder/core/dropzone_selector_plugin";
    import { fontCssVariables } from "@html_builder/plugins/font/font_plugin";
    import { apply_custom_css_style_overrides } from "@html_builder/core/core_builder_action_plugin";
    import { on_bg_color_updated_handlers } from "@html_builder/core/color_style_plugin";
    import { reload_context_processors } from "@html_builder/core/utils";
    import { uncrossable_element_selector, ignore_ctrl_a_predicates } from "@html_builder/core/builder_selection_restriction_plugin";

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
        on_bg_color_updated_handlers: on_bg_color_updated_handlers;
        on_bg_image_hidden_handlers: on_bg_image_hidden_handlers;
        on_cloned_handlers: on_cloned_handlers;
        on_current_options_containers_changed_handlers: on_current_options_containers_changed_handlers;
        on_mobile_view_switched_handlers: on_mobile_view_switched_handlers;
        on_dom_updated_handlers: on_dom_updated_handlers;
        on_element_arrow_moved_handlers: on_element_arrow_moved_handlers;
        on_element_dragged_handlers: on_element_dragged_handlers;
        on_element_dropped_handlers: on_element_dropped_handlers;
        on_element_dropped_near_handlers: on_element_dropped_near_handlers;
        on_element_dropped_over_handlers: on_element_dropped_over_handlers;
        on_element_move_handlers: on_element_move_handlers;
        on_element_out_dropzone_handlers: on_element_out_dropzone_handlers;
        on_element_over_dropzone_handlers: on_element_over_dropzone_handlers;
        on_prepare_drag_handlers: on_prepare_drag_handlers;
        on_removed_handlers: on_removed_handlers;
        on_replicated_handlers: on_replicated_handlers;
        on_saved_handlers: on_saved_handlers;
        on_shape_computed_handlers: on_shape_computed_handlers;
        on_snippet_dragged_handlers: on_snippet_dragged_handlers;
        on_snippet_dropped_handlers: on_snippet_dropped_handlers;
        on_snippet_dropped_near_handlers: on_snippet_dropped_near_handlers;
        on_snippet_dropped_over_handlers: on_snippet_dropped_over_handlers;
        on_snippet_move_handlers: on_snippet_move_handlers;
        on_snippet_out_dropzone_handlers: on_snippet_out_dropzone_handlers;
        on_snippet_over_dropzone_handlers: on_snippet_over_dropzone_handlers;
        on_target_hidden_handlers: on_target_hidden_handlers;
        on_target_revealed_handlers: on_target_revealed_handlers;
        on_target_shown_handlers: on_target_shown_handlers;
        on_will_clone_handlers: on_will_clone_handlers;
        on_will_remove_handlers: on_will_remove_handlers;
        on_will_restore_containers_handlers: on_will_restore_containers_handlers;
        on_will_save_handlers: on_will_save_handlers;
        on_will_save_element_handlers: on_will_save_element_handlers;
        on_will_setup_editor_handlers: on_will_setup_editor_handlers;
        on_ready_to_save_document_handlers: on_ready_to_save_document_handlers;

        // Overrides
        after_setup_editor_overrides: after_setup_editor_overrides;
        apply_custom_css_style_overrides: apply_custom_css_style_overrides;
        save_elements_overrides: save_elements_overrides;

        // Predicates
        should_keep_overlay_options_predicates: should_keep_overlay_options_predicates;
        should_show_overlay_buttons_of_ancestor_predicates: should_show_overlay_buttons_of_ancestor_predicates;
        is_draggable_predicates: is_draggable_predicates;
        is_element_in_invisible_panel_predicates: is_element_in_invisible_panel_predicates;
        is_node_empty_predicates: is_node_empty_predicates;
        is_valid_for_sibling_dropzone_predicates: is_valid_for_sibling_dropzone_predicates;
        ignore_ctrl_a_predicates: ignore_ctrl_a_predicates;

        // Processors
        reload_context_processors: reload_context_processors;
        snippet_preview_dialog_stylesheets_processors: snippet_preview_dialog_stylesheets_processors;

        // Providers
        auto_unfold_container_providers: auto_unfold_container_providers;
        background_filter_target_providers: background_filter_target_providers;
        background_shape_groups_providers: background_shape_groups_providers;
        background_shape_target_providers: background_shape_target_providers;
        clone_disabled_reason_providers: clone_disabled_reason_providers;
        default_shape_providers: default_shape_providers;
        dirty_els_providers: dirty_els_providers;
        image_shape_groups_providers: image_shape_groups_providers;
        options_container_top_buttons_providers: options_container_top_buttons_providers;
        remove_disabled_reason_providers: remove_disabled_reason_providers;
        target_element_providers: target_element_providers;

        // Data
        builder_actions: builder_actions;
        builder_components: builder_components;
        builder_header_middle_buttons: builder_header_middle_buttons;
        container_title: container_title;
        content_editable_selectors: content_editable_selectors;
        content_not_editable_selectors: content_not_editable_selectors;
        dropzone_selectors: dropzone_selectors;
        elements_to_options_title_components: elements_to_options_title_components;
        fontCssVariables: fontCssVariables;
        get_overlay_buttons: get_overlay_buttons;
        has_overlay_options: has_overlay_options;
        is_movable_selectors: is_movable_selectors;
        is_unremovable_selectors: is_unremovable_selectors;
        lower_panel_entries: lower_panel_entries;
        mark_color_level_selector_params: mark_color_level_selector_params;
        no_parent_containers: no_parent_containers;
        savable_selectors: savable_selectors;
        so_content_addition_selectors: so_content_addition_selectors;
        so_snippet_addition_selectors: so_snippet_addition_selectors;
        snippet_preview_dialog_bundles: snippet_preview_dialog_bundles;
        builder_options_render_context: builder_options_render_context;
        uncrossable_element_selector: uncrossable_element_selector;
    }
}
