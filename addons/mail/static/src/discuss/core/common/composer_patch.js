import { Composer } from "@mail/core/common/composer";
import { ChannelCommandSuggestionPlugin } from "@mail/discuss/core/common/suggestion/channel_command_suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get wysiwygConfig() {
        const config = super.wysiwygConfig;
        return { ...config, Plugins: [...config.Plugins, ChannelCommandSuggestionPlugin] };
    },
});
