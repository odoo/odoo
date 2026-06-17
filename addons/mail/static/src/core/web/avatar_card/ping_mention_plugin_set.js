import { MentionPlugin } from "@mail/core/common/plugin/mention_plugin";
import { PingMentionPlugin } from "@mail/core/web/avatar_card/ping_mention_plugin";

import { MailFullComposerSuggestionPlugin } from "@mail/views/web/fields/html_composer_message_field/mail_full_composer_suggestion_plugin";

// Do not include in general plugin sets file to limit assets bundle contamination.

export const PING_MENTION_PLUGINS = [
    MailFullComposerSuggestionPlugin,
    MentionPlugin,
    PingMentionPlugin,
];
