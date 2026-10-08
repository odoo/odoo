import { Message } from "@mail/core/common/message_model";
import { patchModel } from "@mail/model/export";

export const messagePatch = patchModel(Message, {
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
});
