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
        if (thread?.channel?.channel_type === "livechat") {
            return !thread.composerDisabled && !thread.composerHidden;
        }
        return super.canReplyTo(thread);
    },
    get isTranslatable() {
        return (
            super.isTranslatable ||
            (this.store.hasMessageTranslationFeature &&
                this.channel_id?.channel_type === "livechat" &&
                this.store.self?.main_user_id?.share === false)
        );
    },
};
patch(Message.prototype, messagePatch);
