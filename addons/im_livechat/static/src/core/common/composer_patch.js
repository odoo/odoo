import { Composer } from "@mail/core/common/composer";
import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get placeholder() {
        if (this.thread?.channel?.selfMemberType === "visitor") {
            return _t("Say something...");
        }
        return super.placeholder;
    },
    get wysiwygConfig() {
        const config = super.wysiwygConfig;
        if (
            this.props.composer.targetThread?.channel?.channel_type !== "livechat" ||
            this.thread?.channel?.selfMemberType !== "visitor"
        ) {
            return config;
        }
        // visitors cannot mention partners
        return { ...config, Plugins: config.Plugins.filter((P) => P !== PartnerSuggestionPlugin) };
    },
});
