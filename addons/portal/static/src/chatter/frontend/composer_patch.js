import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get showComposerAvatar() {
        return super.showComposerAvatar || (this.compact && this.props.composer.portalComment);
    },

    get shouldHideFromMessageListOnDelete() {
        return this.env.inFrontendPortalChatter || super.shouldHideFromMessageListOnDelete;
    },
});
