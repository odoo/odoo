import { Record, fields } from "@mail/core/common/record";

export class ChatbotScript extends Record {
    static _name = "chatbot.script";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    title;
    isLivechatTourRunning = false;
    operator_partner_id = fields.One("res.partner");
}
ChatbotScript.register();
