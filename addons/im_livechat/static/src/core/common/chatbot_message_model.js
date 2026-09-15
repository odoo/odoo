import { fields, Record } from "@mail/model/export";

export class ChatbotMessage extends Record {
    static _name = "chatbot.message";

    /** @type {number} */
    id;
    mail_message_id = fields.One("mail.message");
    script_step_id = fields.One("chatbot.script.step");
    user_answer_chatbot_message_ids = fields.Many("chatbot.message");
    user_script_answer_id = fields.One("chatbot.script.answer");
}
ChatbotMessage.register();
