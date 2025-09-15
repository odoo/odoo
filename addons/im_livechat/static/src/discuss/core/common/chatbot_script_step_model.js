import { fields, Record } from "@mail/core/common/record";

export class ChatbotScriptStep extends Record {
    static id = "id";
    static _name = "chatbot.script.step";

    /** @type {number} */
    id;
    /** @type {string} */
    message;
    /** @type {"free_input_multi"|"free_input_single"|"question_email"|"question_phone"|"question_selection"|"text"|"forward_operator"} */
    step_type;
    isLast = false;
    answer_ids = fields.Many("chatbot.script.answer");
}
ChatbotScriptStep.register();
