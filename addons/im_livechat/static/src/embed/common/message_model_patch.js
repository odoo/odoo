import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.disableChatbotAnswers = false;
    },

    get notificationHidden() {
        if (this.thread.channel?.channel_type !== "livechat" || !this.notificationType) {
            return super.notificationHidden;
        }
        return this.notificationType === "channel-left";
    },
};
patch(Message.prototype, messagePatch);
