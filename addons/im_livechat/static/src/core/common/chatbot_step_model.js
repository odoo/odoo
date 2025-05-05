import { AND, fields, Record } from "@mail/core/common/record";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

    operatorFound = false;
    scriptStep = fields.One("chatbot.script.step");
    message = fields.One("mail.message", { inverse: "chatbotStep" });
    answer_ids = fields.Many("chatbot.script.answer", {
        compute() {
            return this.scriptStep?.answer_ids;

        },
    });
    selectedAnswer = fields.One("chatbot.script.answer");
    type = fields.Attr("", {
        compute() {
            return this.scriptStep?.type;
        },
    });
    isLast = false;

    get expectAnswer() {
        return [
            "free_input_multi",
            "free_input_single",
            "question_selection",
            "question_email",
            "question_phone",
        ].includes(this.type);
    }
}
ChatbotStep.register();
