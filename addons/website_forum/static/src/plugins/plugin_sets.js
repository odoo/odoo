import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { ForumFontTypePlugin } from "./font_type_plugin";
import { ForumHistoryPlugin } from "./history_plugin";
import { ForumFontSizePlugin } from "./font_size_plugin";

const removedPlugins = new Set(["colorUi", "file", "iconColor"]);

const customPlugins = {
    fontType: ForumFontTypePlugin,
    fontSize: ForumFontSizePlugin,
    history: ForumHistoryPlugin,
};

export const FULL_EDIT_PLUGINS = MAIN_PLUGINS.filter((P) => !removedPlugins.has(P.id)).map(
    (P) => customPlugins[P.id] || P
);

const fullEditOnlyPlugins = new Set(["link", "linkPaste", "mediaUrlPaste", "imageCrop", "media"]);

export const BASIC_PLUGINS = FULL_EDIT_PLUGINS.filter((P) => !fullEditOnlyPlugins.has(P.id));
