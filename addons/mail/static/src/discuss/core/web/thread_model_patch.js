import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    onPinStateUpdated() {
        super.onPinStateUpdated();
        if (!this.displayToSelf && !this.isLocallyPinned && this.eq(this.store.discuss.thread)) {
            if (this.store.discuss.isActive) {
                const newThread =
                    this.store.discuss.channels.threads.find(
                        (thread) => thread.displayToSelf || thread.isLocallyPinned
                    ) || this.store.inbox;
                newThread.setAsDiscussThread();
            } else {
                this.store.discuss.thread = undefined;
            }
        }
    },
});
