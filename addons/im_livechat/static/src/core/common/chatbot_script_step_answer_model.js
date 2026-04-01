import { Record } from "@mail/core/common/record";

export class ChatbotScriptStepAnswer extends Record {
    static id = "id";
    static _name = "chatbot.script.answer";

    /** @type {number} */
    id;
    /** @type {string} */
    label;
    /** @type {string|false} */
    redirect_link;
}
ChatbotScriptStepAnswer.register();
