import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.disableChatbotAnswers = false;
        this.isWelcomeMessage = this.computed(
            () =>
                this.thread?.channel?.hasWelcomeMessage &&
                this.eq(this.thread.channel.livechatWelcomeMessage)
        );
    },

    get notificationHidden() {
        if (this.thread.channel?.channel_type !== "livechat" || !this.notificationType) {
            return super.notificationHidden;
        }
        return this.notificationType === "channel-left";
    },

    get canCopyMessageText() {
        return super.canCopyMessageText && !this.isWelcomeMessage;
    },

    get canReplyTo() {
        return super.canReplyTo && !this.isWelcomeMessage;
    },

    get canAddReaction() {
        return super.canAddReaction && !this.isWelcomeMessage;
    },
};
patch(Message.prototype, messagePatch);
