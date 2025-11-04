import { ChatGPTTranslatePlugin } from "@html_editor/main/chatgpt/chatgpt_translate_plugin";
import { ColorPlugin } from "@html_editor/main/font/color_plugin";
import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { FeffPlugin } from "@html_editor/main/feff_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { LinkPlugin } from "@html_editor/main/link/link_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";

import { MailComposerPlugin } from "@mail/core/common/plugin/mail_composer_plugin";
import { MentionPlugin } from "@mail/core/common/plugin/mention_plugin";

export const MAIL_CORE_PLUGINS = [
    ...CORE_PLUGINS,
    ChatGPTTranslatePlugin,
    ColorPlugin,
    FeffPlugin,
    HintPlugin,
    InlineCodePlugin,
    LinkPlugin,
    MailComposerPlugin,
    MentionPlugin,
    ShortCutPlugin,
    TabulationPlugin,
];

export const MAIL_PLUGINS = [...MAIL_CORE_PLUGINS, ToolbarPlugin];
export const MAIL_SMALL_UI_PLUGINS = MAIL_CORE_PLUGINS;
