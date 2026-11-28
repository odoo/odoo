import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {import("models").BrowsingHistoryEntry[]} */
        this.browsingHistory = [];
        /** @type {"idle"|"loading"|"ready"|"error"|"unavailable"} */
        this.browsingHistoryStatus = "idle";
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
