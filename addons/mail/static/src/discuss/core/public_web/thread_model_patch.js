import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    get isEmpty() {
        return !this.channel?.from_message_id && super.isEmpty;
    },
    setAsDiscussThread() {
        super.setAsDiscussThread(...arguments);
        if (!this.channel || !this.channel.displayToSelf) {
            this.isLocallyPinned = true;
        }
    },
};
patch(Thread.prototype, threadPatch);
