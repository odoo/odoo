import { fields, Record } from "@mail/model/export";

export class ChatbotMessage extends Record {
    static _name = "chatbot.message";

    /** @type {number} */
    id;
    script_step_id = fields.One("chatbot.script.step");
    user_script_answer_id = fields.One("chatbot.script.answer");
}
ChatbotMessage.register();
