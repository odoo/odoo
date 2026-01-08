/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/common/chatbot/chatbot_step_model";

import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";

patch(Message, {
    _insert(data) {
        const chatbotStep = this.store.Message.get(data)?.chatbotStep;
        const message = super._insert(...arguments);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep({ ...chatbotStep, ...data.chatbotStep });
        }
        return message;
    },
});
