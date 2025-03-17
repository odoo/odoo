import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/model/record";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Message} */
const messagePatch = {
    setup() {
        super.setup(...arguments);
        this.chatbotStep = Record.one("ChatbotStep", { inverse: "message" });
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
                thread?.selfMember?.persona?.isInternalUser)
        );
    },
    get authorName() {
        if (this.author?.user_livechat_username && this.thread?.channel_type === "livechat") {
            return this.author.user_livechat_username;
        }
        return super.authorName;
    },
};
patch(Message.prototype, messagePatch);
