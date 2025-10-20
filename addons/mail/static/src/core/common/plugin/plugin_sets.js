import { CORE_PLUGINS } from "@html_editor/plugin_sets";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ShortCutPlugin } from "@html_editor/core/shortcut_plugin";
import { InlineCodePlugin } from "@html_editor/main/inline_code";
import { TabulationPlugin } from "@html_editor/main/tabulation_plugin";
import { HintPlugin } from "@html_editor/main/hint_plugin";
import { MailComposerPlugin } from "@mail/core/common/plugin/mail_composer_plugin";
import { MailSuggestionPlugin } from "@mail/core/common/plugin/mail_suggestion_plugin";
import { MailSuggestionPartnerPlugin } from "@mail/core/common/plugin/mail_suggestion_partner_plugin";
import { MailSuggestionEmojiPlugin } from "@mail/core/common/plugin/mail_suggestion_emoji_plugin";
import { MailSuggestionCannedResponsePlugin } from "@mail/core/common/plugin/mail_suggestion_canned_response_plugin";
import { MailSuggestionChannelCommandPlugin } from "@mail/core/common/plugin/mail_suggestion_channel_command_plugin";
import { MailSuggestionThreadPlugin } from "@mail/core/common/plugin/mail_suggestion_thread_plugin";
import { ChatGPTTranslatePlugin } from "@html_editor/main/chatgpt/chatgpt_translate_plugin";
import { PowerboxPlugin } from "@html_editor/main/powerbox/powerbox_plugin";

export const MAIL_CORE_PLUGINS = [
    ...CORE_PLUGINS,
    ChatGPTTranslatePlugin,
    HintPlugin,
    InlineCodePlugin,
    MailComposerPlugin,
    MailSuggestionCannedResponsePlugin,
    MailSuggestionChannelCommandPlugin,
    MailSuggestionEmojiPlugin,
    MailSuggestionPartnerPlugin,
    MailSuggestionPlugin,
    MailSuggestionThreadPlugin,
    PowerboxPlugin,
    ShortCutPlugin,
    TabulationPlugin,
];

export const MAIL_PLUGINS = [...CORE_PLUGINS, ...MAIL_CORE_PLUGINS, ToolbarPlugin];
export const MAIL_SMALL_UI_PLUGINS = MAIL_PLUGINS;
