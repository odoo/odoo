import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.isDisplayedInDiscussAppDesktop = fields.Attr(undefined, {
            /** @this {import("models").DiscussChannel} */
            compute() {
                return Boolean(
                    this.discussAppAsThread &&
                        this.store.discuss.isActive &&
                        !this.store.env.services.ui.isSmall
                );
            },
        });
    },
    computeIsDisplayed() {
        return this.isDisplayedInDiscussAppDesktop || super.computeIsDisplayed();
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
