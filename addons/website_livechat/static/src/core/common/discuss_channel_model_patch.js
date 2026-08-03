import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").DiscussChannel} */
const discussChannelPatch = {
    setup() {
        super.setup(...arguments);
        this.requested_by_operator = false;
    },
    get hasWelcomeMessage() {
        // the first message of the agent requesting the chat acts as the welcome message
        return super.hasWelcomeMessage && !this.requested_by_operator;
    },
};
patch(DiscussChannel.prototype, discussChannelPatch);
