/* @odoo-module */

import { ChatbotStep } from "@im_livechat/embed/chatbot/chatbot_step_model";

import { insertMessage } from "@mail/core/common/message_service";
import { patchFn } from "@mail/utils/common/patch";

patchFn(insertMessage, function (data) {
    const message = this._super(data);
    if (data.chatbotStep) {
        message.chatbotStep = new ChatbotStep(data.chatbotStep);
    }
    return message;
});
