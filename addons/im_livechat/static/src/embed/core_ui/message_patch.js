/* @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

Message.props.push("isTypingMessage?");

patch(Message.prototype, {
    setup() {
        super.setup();
        this.session = session;
    },

    get authorName() {
        if (this.props.message.originThread?.type === "livechat") {
            return this.props.author.user_livechat_username || super.authorName;
        }
        return super.authorName;
    },

    /**
     * @param {import("@im_livechat/embed/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return this.threadService.post(this.props.message.originThread, answer.label);
    },
});
