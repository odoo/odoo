import { Message } from "@mail/core/common/message_model";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    async remove({ removeFromThread = false } = {}) {
        const data = await super.remove(...arguments);
        if (this.thread && removeFromThread) {
            this.thread.messages.forEach((message) => {
                message.rating_stats = this.thread.rating_stats;
            });
        }
        return data;
    },
};
patch(Message.prototype, messagePatch);
