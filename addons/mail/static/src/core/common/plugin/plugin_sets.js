import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { MailComposerPlugin } from "@mail/core/common/plugin/mail_composer_plugin";
import { ChatGPTTranslatePlugin } from "@html_editor/main/chatgpt/chatgpt_translate_plugin";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";
import { MailSuggestionPlugin } from "./mail_suggestion_plugin";

export const MAIL_CORE_PLUGINS = [
    ...CORE_PLUGINS,
    ChatGPTTranslatePlugin,
    HintPlugin,
    InlineCodePlugin,
    MailComposerPlugin,
    MailSuggestionPlugin,
    PowerboxPlugin,
    ShortCutPlugin,
    TabulationPlugin,
];

export const MAIL_PLUGINS = [...CORE_PLUGINS, ...MAIL_CORE_PLUGINS, ToolbarPlugin];
