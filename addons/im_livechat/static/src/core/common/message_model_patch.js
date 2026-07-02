import { Message } from "@mail/core/common/message_model";
import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.chatbotStep = fields.One("ChatbotStep", { inverse: "message" });
        this.disableChatbotAnswers = false;
    },
    canReplyTo(thread) {
        if (thread?.channel?.channel_type === "livechat") {
            return !this.isEmpty && !thread.composerDisabled && !thread.channel.composerHidden;
        }
        return super.canReplyTo(thread);
    },
    get isTranslatable() {
        return (
            super.isTranslatable ||
            (this.store.hasMessageTranslationFeature &&
                this.channel_id?.channel_type === "livechat" &&
                this.store.self_user?.share === false)
        );
    },
    get notificationHidden() {
        if (
            this.notificationType === "channel-left" &&
            this.channel_id?.self_member_id?.livechat_member_type === "visitor"
        ) {
            return true;
        }
        return super.notificationHidden;
    },
};
patch(Message.prototype, messagePatch);
