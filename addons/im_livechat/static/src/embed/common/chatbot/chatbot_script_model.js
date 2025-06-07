import { Record } from "@mail/core/common/record";

export class ChatbotScript extends Record {
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
    isLivechatTourRunning = false;
    partner = Record.one("Persona");
    welcomeSteps = Record.many("chatbot.script.step");
}
ChatbotScript.register();
