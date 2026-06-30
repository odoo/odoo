import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.chatbotStep = fields.One("ChatbotStep", { inverse: "message" });
    },
    canReplyTo(thread) {
        return (
            super.canReplyTo(thread) &&
            (thread?.channel_type !== "livechat" || !thread.composerDisabled)
        );
    },
    isTranslatable(thread) {
        return (
            super.isTranslatable(thread) ||
            (this.store.hasMessageTranslationFeature &&
                thread?.channel_type === "livechat" &&
                this.store.self?.main_user_id?.share === false)
        );
    },
};
patch(Message.prototype, messagePatch);
