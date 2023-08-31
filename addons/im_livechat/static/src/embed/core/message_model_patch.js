/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

import { Message } from "@mail/core/common/message_model";

import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

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
    get isSelfAuthored() {
        if (this.originThread.type !== "livechat") {
            return super.isSelfAuthored;
        }
        return !this.author || this.author?.id === session.livechatData.options.current_partner_id;
    },

    get editable() {
        return this.originThread.type !== "livechat" && this._super();
    },
});
