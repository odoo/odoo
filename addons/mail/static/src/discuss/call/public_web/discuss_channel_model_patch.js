import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const DiscussChannelPatch = {
    get isCallDisplayedInChatWindow() {
        return (
            super.isCallDisplayedInChatWindow &&
            (this.store.env.services.ui.isSmall || !this.store.discuss.isActive)
        );
    },
};
patch(DiscussChannel.prototype, DiscussChannelPatch);
