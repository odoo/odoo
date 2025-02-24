import { CORE_PLUGINS } from "@html_editor/plugin_sets_core_main";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";

import { ComposerPlugin } from "@mail/core/common/plugins/composer_plugin";
import { SuggestionPlugin } from "@mail/core/common/plugins/suggestion_plugin";

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
