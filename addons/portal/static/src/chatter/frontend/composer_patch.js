import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    setup() {
        super.setup();
        if (this.env.inFrontendPortalChatter) {
            this.suggestion = undefined;
        }
    },

    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },
});
