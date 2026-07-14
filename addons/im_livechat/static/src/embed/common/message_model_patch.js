import { Message } from "@mail/core/common/message_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";

patch(Message.prototype, {
    setup() {
        super.setup();
        this.chatbotStep = Record.one("ChatbotStep", { inverse: "message" });
    },
    canAddReaction(thread) {
        return (
            super.canAddReaction(thread) &&
            (thread?.channel_type !== "livechat" ||
                this.store.env.services["im_livechat.livechat"].state === SESSION_STATE.PERSISTED)
        );
    },
    canReplyTo(thread) {
        return (
            super.canReplyTo(thread) &&
            (thread?.channel_type !== "livechat" ||
                this.store.env.services["im_livechat.chatbot"].inputEnabled)
        );
    },
});
