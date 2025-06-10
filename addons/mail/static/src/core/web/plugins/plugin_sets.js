import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { ComposerPlugin } from "./composer_plugin";

import { SuggestionPlugin } from "./suggestion_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";

export const MAIL_PLUGINS = [
    ...CORE_PLUGINS,
    InlineCodePlugin,
    HintPlugin,
    ComposerPlugin,
    ShortCutPlugin,
    TabulationPlugin,
    ToolbarPlugin,
    SuggestionPlugin,
];

export const MAIL_SMALL_UI_PLUGINS = [
    ...CORE_PLUGINS,
    InlineCodePlugin,
    HintPlugin,
    ComposerPlugin,
    ShortCutPlugin,
    TabulationPlugin,
    SuggestionPlugin,
];
