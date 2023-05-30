/** @odoo-module */

import { MessageService } from "@mail/core/message_service";
import { patch } from "@web/core/utils/patch";
import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

patch(MessageService.prototype, "im_livechat", {
    insert(data) {
        const message = this._super(data);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep(data.chatbotStep);
        }
        return message;
    },
});
