/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message, {
    insert(data) {
        const message = super.insert(data);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep(data.chatbotStep);
        }
        return message;
    },
});

patch(Message.prototype, {
    get editable() {
        return this.originThread.type !== "livechat" && this._super();
    },
});
