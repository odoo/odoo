import { patch } from "@web/core/utils/patch";
import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";

import { rpcWithEnv } from "@mail/utils/common/misc";
let rpc;

patch(Thread.prototype, {
    setup() {
        super.setup();
        rpc = rpcWithEnv(this.env);

        /** @type {'loaded'|'loading'|'error'|undefined} */
        this.pinnedMessagesState = undefined;
        this.pinnedMessages = Record.many("Message", {
            compute() {
                return this.allMessages.filter((m) => m.pinned_at);
            },
            sort: (m1, m2) => {
                if (m1.pinned_at === m2.pinned_at) {
                    return m1.id - m2.id;
                }
                return m1.pinned_at < m2.pinned_at ? 1 : -1;
            },
        });
    },

    /**
     * @param {import("models").Thread} channel
     */
    async fetchPinnedMessages() {
        if (
            this.model !== "discuss.channel" ||
            ["loaded", "loading"].includes(this.pinnedMessagesState)
        ) {
            return;
        }
        this.pinnedMessagesState = "loading";
        try {
            const messagesData = await rpc("/discuss/channel/pinned_messages", {
                channel_id: this.id,
            });
            this.store.Message.insert(messagesData, { html: true });
            this.pinnedMessagesState = "loaded";
        } catch (e) {
            this.pinnedMessagesState = "error";
            throw e;
        }
    },
});
