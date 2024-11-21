import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup();
        this.hasEveryoneSeen = Record.attr(false, {
            /** @this {import("models").Message} */
            compute() {
                return this.thread?.membersThatCanSeen.every((m) => m.hasSeen(this));
            },
        });
        this.isMessagePreviousToLastSelfMessageSeenByEveryone = Record.attr(false, {
            /** @this {import("models").Message} */
            compute() {
                if (!this.thread?.lastSelfMessageSeenByEveryone) {
                    return false;
                }
                return this.id < this.thread.lastSelfMessageSeenByEveryone.id;
            },
        });
        this.mentionedChannelPromises = [];
    },
    /**
     * @override
     */
    async edit(body, attachments = [], { mentionedChannels = [], mentionedPartners = [] } = {}) {
        const validChannels = (await Promise.all(this.mentionedChannelPromises)).filter(
            (channel) => channel !== undefined
        );
        const allChannels = this.store.Thread.insert([...validChannels, ...mentionedChannels]);
        super.edit(body, attachments, {
            mentionedChannels: allChannels,
            mentionedPartners,
        });
    },
};
patch(Message.prototype, messagePatch);
