import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";
import { SESSION_STATE } from "./livechat_service";

/** @type {import("models").Message} */
const messagePatch = {
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
            (thread?.channel_type !== "livechat" || !thread.composerDisabled)
        );
    },
};
patch(Message.prototype, messagePatch);
