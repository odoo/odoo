import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup();
        this.isDisplayedInDiscussAppDesktop = this.computed(() =>
            Boolean(
                this.discussAppAsThread &&
                    this.store.discuss.isActive &&
                    !this.store.env.services.ui.isSmall
            )
        );
    },
    get isDisplayed() {
        return this.isDisplayedInDiscussAppDesktop || super.isDisplayed;
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
