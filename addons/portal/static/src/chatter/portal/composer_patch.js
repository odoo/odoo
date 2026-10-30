import { Composer } from "@mail/core/common/composer";
import { PartnerSuggestionPlugin } from "@mail/core/common/plugin/suggestion/partner_suggestion_plugin";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get placeholder() {
        if (this.ancestors.inFrontendPortalChatter) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },

    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },

    get wysiwygConfig() {
        const config = super.wysiwygConfig;
        if (!this.ancestors.inFrontendPortalChatter) {
            return config;
        }
        return { ...config, Plugins: config.Plugins.filter((P) => P !== PartnerSuggestionPlugin) };
    },
});
