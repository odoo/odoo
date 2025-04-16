import { Composer } from "@mail/core/common/composer";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup();
        if (this.env.inFrontendPortalChatter) {
            this.suggestion = undefined;
        }
    },

    get placeholder() {
        if (this.env.inFrontendPortalChatter) {
            return _t("Write a message…");
        }
        return super.placeholder;
    },

    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },
});
