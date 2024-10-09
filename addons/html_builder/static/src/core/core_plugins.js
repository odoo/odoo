import { AnchorPlugin } from "./plugins/anchor/anchor_plugin";
import { BuilderActionsPlugin } from "./plugins/builder_actions_plugin";
import { BuilderOptionsPlugin } from "./plugins/builder_options_plugin";
import { BuilderOverlayPlugin } from "./plugins/builder_overlay/builder_overlay_plugin";
import { CachedModelPlugin } from "./plugins/cached_model_plugin";
import { ClonePlugin } from "./plugins/clone/clone_plugin";
import { DragAndDropPlugin } from "./plugins/drag_and_drop/drag_and_drop_plugin";
import { DropZonePlugin } from "./plugins/drop_zone_plugin";
import { DropZoneSelectorPlugin } from "./plugins/dropzone_selector_plugin";
import { GridLayoutPlugin } from "./plugins/grid_layout/grid_layout_plugin";
import { SavePlugin } from "./plugins/save_plugin";
import { MediaWebsitePlugin } from "./plugins/media_website_plugin";
import { MovePlugin } from "./plugins/move/move_plugin";
import { OperationPlugin } from "./plugins/operation_plugin";
import { OverlayButtonsPlugin } from "./plugins/overlay_buttons/overlay_buttons_plugin";
import { RemovePlugin } from "./plugins/remove/remove_plugin";
import { ReplacePlugin } from "./plugins/replace/replace_plugin";
import { SaveSnippetPlugin } from "./plugins/save_snippet/save_snippet_plugin";
import { SetupEditorPlugin } from "./plugins/setup_editor_plugin";
import { VisibilityPlugin } from "./plugins/visibility_plugin";
import { CoreBuilderActionPlugin } from "./plugins/core_builder_action_plugin";

export const CORE_PLUGINS = [
    BuilderOptionsPlugin,
    BuilderActionsPlugin,
    OperationPlugin,
    BuilderOverlayPlugin,
    OverlayButtonsPlugin,
    MovePlugin,
    GridLayoutPlugin,
    DragAndDropPlugin,
    ReplacePlugin,
    RemovePlugin,
    ClonePlugin,
    SaveSnippetPlugin,
    AnchorPlugin,
    DropZonePlugin,
    MediaWebsitePlugin,
    SetupEditorPlugin,
    SavePlugin,
    VisibilityPlugin,
    DropZoneSelectorPlugin,
    CachedModelPlugin,
    CoreBuilderActionPlugin,
];
