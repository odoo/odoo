import {
    MAIN_PLUGINS as MAIN_EDITOR_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { removePlugins } from "@html_builder/utils/utils";
import { AnchorPlugin } from "./anchor/anchor_plugin";
import { BuilderActionsPlugin } from "./builder_actions_plugin";
import { BuilderComponentPlugin } from "./builder_component_plugin";
import { BuilderOptionsPlugin } from "./builder_options_plugin";
import { BuilderOverlayPlugin } from "./builder_overlay/builder_overlay_plugin";
import { CachedModelPlugin } from "./cached_model_plugin";
import { ClonePlugin } from "./clone_plugin";
import { ColorUIPlugin } from "./color_ui_plugin";
import { ImagePlugin } from "./image_plugin";
import { IconPlugin } from "./icon_plugin";
import { CoreBuilderActionPlugin } from "./core_builder_action_plugin";
import { CompositeActionPlugin } from "./composite_action_plugin";
import { CustomizeTabPlugin } from "./customize_tab_plugin";
import { DisableSnippetsPlugin } from "./disable_snippets_plugin";
import { DragAndDropPlugin } from "./drag_and_drop_plugin";
import { DropZonePlugin } from "./drop_zone_plugin";
import { DropZoneSelectorPlugin } from "./dropzone_selector_plugin";
import { GridLayoutPlugin } from "./grid_layout/grid_layout_plugin";
import { MediaWebsitePlugin } from "./media_website_plugin";
import { MovePlugin } from "./move_plugin";
import { OperationPlugin } from "./operation_plugin";
import { OverlayButtonsPlugin } from "./overlay_buttons/overlay_buttons_plugin";
import { RemovePlugin } from "./remove_plugin";
import { SavePlugin } from "./save_plugin";
import { SaveSnippetPlugin } from "./save_snippet_plugin";
import { SetupEditorPlugin } from "./setup_editor_plugin";
import { CoreSetupEditorPlugin } from "./core_setup_editor_plugin";
import { VisibilityPlugin } from "./visibility_plugin";
import { FieldChangeReplicationPlugin } from "./field_change_replication_plugin";
import { BuilderContentEditablePlugin } from "./builder_content_editable_plugin";
import { ImageFieldPlugin } from "@html_builder/plugins/image_field_plugin";
import { MonetaryFieldPlugin } from "@html_builder/plugins/monetary_field_plugin";
import { Many2OneOptionPlugin } from "@html_builder/plugins/many2one_option_plugin";

const mainEditorPluginsToRemove = [
    "PowerButtonsPlugin",
    "DoubleClickImagePreviewPlugin",
    "SeparatorPlugin",
    "StarPlugin",
    "BannerPlugin",
    "MoveNodePlugin",
    "FontFamilyPlugin",
    "SelectionPlaceholderPlugin",
    // Replaced plugins:
    "ColorUIPlugin",
    "ImagePlugin",
    "IconPlugin",
];

export const MAIN_PLUGINS = [
    ...removePlugins(
        [...MAIN_EDITOR_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS],
        mainEditorPluginsToRemove
    ),
    ColorUIPlugin,
    ImagePlugin,
    IconPlugin,
];

export const CORE_PLUGINS = [
    ...MAIN_PLUGINS,
    BuilderOptionsPlugin,
    BuilderActionsPlugin,
    BuilderComponentPlugin,
    OperationPlugin,
    BuilderOverlayPlugin,
    OverlayButtonsPlugin,
    MovePlugin,
    GridLayoutPlugin,
    DragAndDropPlugin,
    RemovePlugin,
    ClonePlugin,
    SaveSnippetPlugin,
    AnchorPlugin,
    DropZonePlugin,
    DisableSnippetsPlugin,
    MediaWebsitePlugin,
    SetupEditorPlugin,
    CoreSetupEditorPlugin,
    SavePlugin,
    VisibilityPlugin,
    DropZoneSelectorPlugin,
    CachedModelPlugin,
    CoreBuilderActionPlugin,
    CompositeActionPlugin,
    CustomizeTabPlugin,
    FieldChangeReplicationPlugin,
    BuilderContentEditablePlugin,
    ImageFieldPlugin,
    MonetaryFieldPlugin,
    Many2OneOptionPlugin,
];
