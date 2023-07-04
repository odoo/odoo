/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

import { MessageService } from "@mail/core/common/message_service";

import { patch } from "@web/core/utils/patch";

patch(MessageService.prototype, {
    insert(data) {
        const message = super.insert(data);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep(data.chatbotStep);
        }
        return message;
    },
});
