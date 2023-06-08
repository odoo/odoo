/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

import { MessageService } from "@mail/core/common/message_service";

import { patch } from "@web/core/utils/patch";

patch(MessageService.prototype, "im_livechat", {
    insert(data) {
        const message = this._super(data);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep(data.chatbotStep);
        }
        return message;
    },
});
