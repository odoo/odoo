import { Record } from "@mail/model/export";

export class ChatbotScriptStepAnswer extends Record {
    static _name = "chatbot.script.answer";

    /** @type {number} */
    id;
    /** @type {string} */
    label;
    /** @type {string|false} */
    redirect_link;
}
ChatbotScriptStepAnswer.register();
