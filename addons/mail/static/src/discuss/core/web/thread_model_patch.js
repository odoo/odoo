import { Thread } from "@mail/core/common/thread_model";

import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.foldStateCount = 0;
    },
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
    /**
     * @param {import("models").Message} initialMessage
     */
    async createSubChannel(initialMessage) {
        const data = await this.store.env.services.orm.call(
            "discuss.channel",
            "create_sub_channel",
            [[this.id]],
            {
                initial_message_id: initialMessage?.id,
            }
        );
        this.store.insert(data);
    },
});
