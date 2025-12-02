import { AND, fields, Record } from "@mail/core/common/record";
import { createDocumentFragmentFromContent } from "@web/core/utils/html";

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
    rawAnswer = fields.Html("");
    step_type = fields.Attr("", {
        compute() {
            return this.scriptStep?.step_type;
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
        ].includes(this.step_type);
    }

    get answer() {
        switch (this.step_type) {
            case "free_input_multi":
            case "free_input_single":
            case "question_email":
            case "question_phone":
                return createDocumentFragmentFromContent(this.rawAnswer).body.textContent;
            case "question_selection":
                return this.selectedAnswer?.label;
            default:
                return "";
        }
    }
}
ChatbotStep.register();
