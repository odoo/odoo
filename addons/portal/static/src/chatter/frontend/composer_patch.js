import { Composer } from "@mail/core/common/composer";
import { SuggestionPlugin } from "@mail/core/common/plugins/suggestion_plugin";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get wysiwygConfigs() {
        const configs = super.wysiwygConfigs;
        if (this.env.inFrontendPortalChatter) {
            configs.Plugins = configs.Plugins.filter((plugin) => plugin !== SuggestionPlugin);
            configs.classList.push("o-mail-Composer-input-portal");
        }
        return configs;
    },

    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },
});
