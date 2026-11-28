import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    get notificationHidden() {
        if (
            this.thread.channel?.channel_type === "livechat" &&
            this.notificationType === "channel-left"
        ) {
            return true;
        }
        return super.notificationHidden;
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
