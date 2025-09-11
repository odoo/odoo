import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { ForumFontPlugin } from "./font_plugin";
import { ForumHistoryPlugin } from "./history_plugin";

const removedPlugins = new Set(["colorUi", "iconColor"]);

const customPlugins = {
    font: ForumFontPlugin,
    history: ForumHistoryPlugin,
};

export const FULL_EDIT_PLUGINS = MAIN_PLUGINS.filter((P) => !removedPlugins.has(P.id)).map(
    (P) => customPlugins[P.id] || P
);

const fullEditOnlyPlugins = new Set(["link", "linkPaste", "mediaUrlPaste", "imageCrop", "media"]);

export const BASIC_PLUGINS = FULL_EDIT_PLUGINS.filter((P) => !fullEditOnlyPlugins.has(P.id));
