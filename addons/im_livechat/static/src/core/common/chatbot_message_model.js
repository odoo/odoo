import { fields, Record } from "@mail/model/export";
import { createElementFromContent } from "@mail/utils/common/html";

export class ChatbotMessage extends Record {
    static _name = "chatbot.message";

    /** @type {number} */
    id;
    discuss_channel_id = fields.One("discuss.channel", { inverse: "chatbot_message_ids" });
    script_step_id = fields.One("chatbot.script.step");
    user_script_answer_id = fields.One("chatbot.script.answer");
    user_raw_answer = fields.Html("");

    get expectAnswer() {
        return this.script_step_id?.expectAnswer;
    }

    get answer() {
        switch (this.script_step_id?.step_type) {
            case "free_input_multi":
            case "free_input_single":
            case "question_email":
            case "question_phone":
                return createElementFromContent(this.user_raw_answer).textContent;
            case "question_selection":
                return this.user_script_answer_id?.name;
            default:
                return "";
        }
    }
}
ChatbotMessage.register();
