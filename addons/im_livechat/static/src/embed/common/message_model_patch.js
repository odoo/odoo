import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup();
        this.chatbotStep = Record.one("ChatbotStep", { inverse: "message" });
        this.disableChatbotAnswers = false;
    },
    canAddReaction(thread) {
        return (
            super.canAddReaction(thread) &&
            (thread?.channel_type !== "livechat" || !thread.isTransient)
        );
    },
    canReplyTo(thread) {
        return (
            super.canReplyTo(thread) &&
            (thread?.channel_type !== "livechat" || !thread.composerDisabled)
        );
    },
};
patch(Message.prototype, messagePatch);
