import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyAll(thread) {
        return this.canForward(thread) && !this.is_note;
    },
    canForward(thread) {
        if (!thread) {
            return false;
        }
        return (
            !["discuss.channel", "mail.box"].includes(thread.model) &&
            ["comment", "email"].includes(this.message_type)
        );
    },
};
patch(Message.prototype, messagePatch);
