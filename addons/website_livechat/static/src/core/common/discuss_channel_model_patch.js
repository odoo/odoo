import { DiscussChannel } from "@mail/discuss/core/common/discuss_channel_model";
import { patchModel } from "@mail/model/export";

export const discussChannelPatch = patchModel(DiscussChannel, {
    setup() {
        super.setup(...arguments);
        this.requested_by_operator = false;
    },
    get hasWelcomeMessage() {
        // the first message of the agent requesting the chat acts as the welcome message
        return super.hasWelcomeMessage && !this.requested_by_operator;
    },
});
