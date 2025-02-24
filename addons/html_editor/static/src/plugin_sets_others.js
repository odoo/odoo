import { MAIN_PLUGINS } from "./plugin_sets_core_main";
import { CollaborationOdooPlugin } from "./others/collaboration/collaboration_odoo_plugin";
import { CollaborationPlugin } from "./others/collaboration/collaboration_plugin";
import { CollaborationSelectionAvatarPlugin } from "./others/collaboration/collaboration_selection_avatar_plugin";
import { CollaborationSelectionPlugin } from "./others/collaboration/collaboration_selection_plugin";
import { DynamicPlaceholderPlugin } from "./others/dynamic_placeholder_plugin";
import { EmbeddedComponentPlugin } from "./others/embedded_component_plugin";
import { TableOfContentPlugin } from "@html_editor/others/embedded_components/plugins/table_of_content_plugin/table_of_content_plugin";
import { ToggleBlockPlugin } from "@html_editor/others/embedded_components/plugins/toggle_block_plugin/toggle_block_plugin";
import { VideoPlugin } from "@html_editor/others/embedded_components/plugins/video_plugin/video_plugin";
import { QWebPlugin } from "./others/qweb_plugin";

/**
 * @typedef { Object } SharedMethods
 *
 * Others
 * @property { import("./others/collaboration/collaboration_odoo_plugin").CollaborationOdooShared } collaborationOdoo
 * @property { import("./others/collaboration/collaboration_plugin").CollaborationShared } collaboration
 * @property { import("./others/dynamic_placeholder_plugin").DynamicPlaceholderShared } dynamicPlaceholder
 */

export const COLLABORATION_PLUGINS = [
    CollaborationPlugin,
    CollaborationOdooPlugin,
    CollaborationSelectionPlugin,
    CollaborationSelectionAvatarPlugin,
];

export const EMBEDDED_COMPONENT_PLUGINS = [
    EmbeddedComponentPlugin,
    TableOfContentPlugin,
    ToggleBlockPlugin,
    VideoPlugin,
];

export const DYNAMIC_PLACEHOLDER_PLUGINS = [DynamicPlaceholderPlugin, QWebPlugin];

export const EXTRA_PLUGINS = [
    ...COLLABORATION_PLUGINS,
    ...MAIN_PLUGINS,
    ...EMBEDDED_COMPONENT_PLUGINS,
    QWebPlugin,
];
