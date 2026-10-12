import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { ForumFontTypePlugin } from "./font_type_plugin";

const removedPlugins = new Set(["colorUi", "file", "iconColor", "tableBorder", "powerButtons", "fontFamily", "fontSize"]);

const customPlugins = {
    fontType: ForumFontTypePlugin,
};

export const FULL_EDIT_PLUGINS = MAIN_PLUGINS.filter((P) => !removedPlugins.has(P.id)).map(
    (P) => customPlugins[P.id] || P
);

const fullEditOnlyPlugins = new Set(["link", "linkPaste", "mediaUrlPaste", "imageCrop", "media"]);

export const BASIC_PLUGINS = FULL_EDIT_PLUGINS.filter((P) => !fullEditOnlyPlugins.has(P.id));
