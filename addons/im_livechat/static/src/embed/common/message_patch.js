import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { SESSION_STATE } from "./livechat_service";
import { isEmbedLivechatEnabled } from "./misc";

Message.props.push("isTypingMessage?");

patch(Message.prototype, {
    setup() {
        super.setup();
        this.url = url;
        this.isEmbedLivechatEnabled = isEmbedLivechatEnabled;
    },

    get quickActionCount() {
        if (!isEmbedLivechatEnabled(this.env)) {
            return super.quickActionCount;
        }
        return this.props.thread?.channel_type === "livechat" ? 2 : super.quickActionCount;
    },

    get canAddReaction() {
        if (!isEmbedLivechatEnabled(this.env)) {
            return super.canAddReaction;
        }
        return (
            super.canAddReaction &&
            (this.props.thread?.channel_type !== "livechat" ||
                this.env.services["im_livechat.livechat"].state === SESSION_STATE.PERSISTED)
        );
    },

    get canReplyTo() {
        if (!isEmbedLivechatEnabled(this.env)) {
            return super.canReplyTo;
        }
        return (
            super.canReplyTo &&
            (this.props.thread?.channel_type !== "livechat" ||
                this.env.services["im_livechat.chatbot"].inputEnabled)
        );
    },

    /**
     * @param {import("@im_livechat/embed/common/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return this.threadService.post(this.props.message.thread, answer.label);
    },
});
