import { fields, Record } from "@mail/model/export";

export class ChatbotScriptStep extends Record {
    static _name = "chatbot.script.step";

    chatbot_script_id = fields.One("chatbot.script");
    /** @type {number} */
    id;
    /** @type {boolean} */
    is_last;
    /** @type {string} */
    message;
    /** @type {"free_input_multi"|"free_input_single"|"question_email"|"question_phone"|"question_selection"|"text"|"forward_operator"} */
    step_type;
    isLast = false;
    answer_ids = fields.Many("chatbot.script.answer");
}
ChatbotScriptStep.register();
