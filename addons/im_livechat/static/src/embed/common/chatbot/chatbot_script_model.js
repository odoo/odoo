import { Record } from "@mail/core/common/record";

export class ChatbotScript extends Record {
    static _name = "chatbot.script";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    title;
    isLivechatTourRunning = false;
    operator_partner_id = Record.one("Persona");
    welcome_steps = Record.many("chatbot.script.step");
}
ChatbotScript.register();
