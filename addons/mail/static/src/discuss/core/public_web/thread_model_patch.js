import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup(...arguments);
    },
    get isEmpty() {
        return !this.channel?.from_message_id && super.isEmpty;
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (this.channel && !this.channel?.self_member_id?.is_pinned) {
            this.channel.isLocallyPinned = true;
        }
    },
};
patch(Thread.prototype, threadPatch);
