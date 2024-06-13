import { Record } from "@mail/core/common/record";

export class ChatbotScriptStep extends Record {
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    message;
    /** @type {"free_input_multi"|"free_input_single"|"question_email"|"question_phone"|"question_selection"|"text"|"forward_operator"} */
    type;
    isLast = false;
    answers = Record.many("ChatbotScriptStepAnswer");
}
ChatbotScriptStep.register();
