import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.chatbotStep = fields.One("ChatbotStep", { inverse: "message" });
    },
    get canReplyTo() {
        if (this.thread?.channel?.channel_type === "livechat") {
            return (
                !this.isEmpty &&
                !this.thread.composerDisabled &&
                !this.thread.channel.composerHidden
            );
        }
        return super.canReplyTo;
    },
    get isTranslatable() {
        return (
            super.isTranslatable ||
            (this.store.hasMessageTranslationFeature &&
                this.channel_id?.channel_type === "livechat" &&
                this.store.self_user?.share === false)
        );
    },
};
patch(Message.prototype, messagePatch);
