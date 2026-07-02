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
    get canToggleBookmark() {
        if (this.channel_id?.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return super.canToggleBookmark;
    },
    get canTogglePin() {
        if (this.channel_id?.self_member_id?.livechat_member_type === "visitor") {
            return false;
        }
        return super.canTogglePin;
    },
    get isTranslatable() {
        return (
            super.isTranslatable ||
            (this.store.hasMessageTranslationFeature &&
                this.channel_id?.channel_type === "livechat" &&
                (this.store.self_user?.share === false || !this.isSelfAuthored))
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
