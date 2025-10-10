import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelModelPatch = {
    /** @override */
    openChannel() {
        if (this.store.discuss.isActive && !this.store.env.services.ui.isSmall) {
            this.thread.setAsDiscussThread();
            return true;
        }
        return super.openChannel();
    },
};
patch(DiscussChannel.prototype, discussChannelModelPatch);
