import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyAll(thread) {
        return this.canForward(thread) && !this.isNote && !this.isEmpty;
    },
    /** @param {import("models").Thread} thread */
    canForward(thread) {
        if (!thread || this.isEmpty) {
            return false;
        }
        return (
            thread.model !== "discuss.channel" &&
            ["comment", "email", "email_outgoing"].includes(this.message_type)
        );
    },
};
patch(Message.prototype, messagePatch);
