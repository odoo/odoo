/* @odoo-module */

import { Message, MessageManager } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { ChatbotStep } from "../chatbot/chatbot_step_model";

patch(Message.prototype, {
    get isSelfAuthored() {
        if (this.originThread.type !== "livechat") {
            return super.isSelfAuthored;
        }
        return !this.author || this.author?.id === session.livechatData.options.current_partner_id;
    },
});

patch(MessageManager, {
    insert(data) {
        const message = super.insert(data);
        if (data.chatbotStep) {
            message.chatbotStep = new ChatbotStep(data.chatbotStep);
        }
        return message;
    },
});
