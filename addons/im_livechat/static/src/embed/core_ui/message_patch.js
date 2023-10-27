/* @odoo-module */

import { Message } from "@mail/core/common/message";

import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

Message.props.push("isTypingMessage?");

patch(Message.prototype, "im_livechat", {
    setup() {
        this._super();
        this.url = url;
    },

    /**
     * @param {import("@im_livechat/embed/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return this.threadService.post(this.props.message.originThread, answer.label, {});
    },
});
