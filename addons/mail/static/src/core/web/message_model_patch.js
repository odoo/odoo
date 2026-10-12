import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    get canReplyAll() {
        return this.canForward && !this.isNote && !this.isEmpty;
    },
    get canForward() {
        if (!this.thread || this.isEmpty) {
            return false;
        }
        return (
            !this.thread.channel &&
            ["comment", "email", "email_outgoing"].includes(this.message_type)
        );
    },
};
patch(Message.prototype, messagePatch);
