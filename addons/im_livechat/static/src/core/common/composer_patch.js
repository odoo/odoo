import { Composer } from "@mail/core/common/composer";
import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get wysiwygConfig() {
        const config = super.wysiwygConfig;
        if (
            this.props.composer.targetThread?.channel?.channel_type !== "livechat" ||
            this.store.self_user?.share === false
        ) {
            return config;
        }
        // visitors cannot mention partners
        return { ...config, Plugins: config.Plugins.filter((P) => P !== PartnerSuggestionPlugin) };
    },
});
