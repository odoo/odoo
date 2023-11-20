/* @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";
import { SESSION_STATE } from "./livechat_service";

Message.props.push("isTypingMessage?");

patch(Message.prototype, {
    setup() {
        super.setup();
        this.url = url;
    },

    get quickActionCount() {
        return this.props.thread?.type === "livechat" ? 2 : super.quickActionCount;
    },

    get canAddReaction() {
        return (
            super.canAddReaction &&
            (this.props.thread?.type !== "livechat" ||
                this.env.services["im_livechat.livechat"].state === SESSION_STATE.PERSISTED)
        );
    },

    get canReplyTo() {
        return (
            super.canReplyTo &&
            (this.props.thread?.type !== "livechat" ||
                this.env.services["im_livechat.chatbot"].inputEnabled)
        );
    },

    /**
     * @param {import("@im_livechat/embed/common/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return this.threadService.post(this.props.message.originThread, answer.label);
    },
});
