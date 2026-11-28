import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    get canAddReaction() {
        return super.canAddReaction && (this.thread.channel || this.thread.canPostMessage);
    },
    get canReplyAll() {
        return this.canForward && !this.isNote && !this.isEmpty;
    },
    get canForward() {
        if (!this.thread || this.isEmpty) {
            return false;
        }
        return (
            !this.thread.channel &&
            this.thread.canPostMessage &&
            ["comment", "email", "email_outgoing"].includes(this.message_type)
        );
    },
};
patch(Message.prototype, messagePatch);
