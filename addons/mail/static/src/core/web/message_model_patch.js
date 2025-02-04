import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    /** @param {import("models").Thread} thread the thread where the message is shown */
    canReplyAllandForward(thread) {
        return (
            !["discuss.channel", "mail.box"].includes(thread.model) &&
            ["comment", "email"].includes(this.message_type) &&
            !this.is_note
        );
    },
};
patch(Message.prototype, messagePatch);
