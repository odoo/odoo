import { AND, Record } from "@mail/core/common/record";

export class ChatbotStep extends Record {
    static id = AND("scriptStep", "message");

    operatorFound = false;
    scriptStep = Record.one("chatbot.script.step");
    message = Record.one("mail.message", { inverse: "chatbotStep" });
    answers = Record.many("chatbot.script.answer", {
        compute() {
            return this.scriptStep?.answers;
        },
    });
    completed = false;
    selectedAnswer = Record.one("chatbot.script.answer");
    type = Record.attr("", {
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
