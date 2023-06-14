/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { postMessage } from "@mail/core/common/thread_service";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

Message.props.push("isTypingMessage?");

patch(Message.prototype, "im_livechat", {
    setup() {
        this._super();
        this.session = session;
    },

    /**
     * @param {import("@im_livechat/embed/chatbot/chatbot_step_model").StepAnswer} answer
     */
    answerChatbot(answer) {
        return postMessage(this.props.message.originThread, answer.label, {});
    },
});
